# Draft rulespec-us dispatch: insured status and quarters of coverage

Verification class: statutory conformance. Required expectations come from
published statutory cases and invented declarations only; this issue admits
no population, behavioral or forecast claim. This draft is not filed.

Suggested issue title: `Encode 42 USC 413, 414 and 423(c)(1): quarters of
coverage and fully/currently/disability insured status`.

The offline workspace does not contain rulespec-us issues #1403 or #1416.
The structure below approximates the requested dispatch format; the
orchestrator must map its field names to those templates before filing.
No request was made to GitHub or any other external service.

## Problem and dispatch scope

The task brief reports that rulespec-us encodes 402, 415, 416(l) and 426,
but has no pinned 413, 414 or 423(c) rule. Consequently the Python reference
cannot yet run an Axiom differential for insured status. Add the statutory
rules below and companion examples, then supply the immutable rule revision,
corpus revision, module hashes and runtime contract. A differential remains
diagnostic until those exact versions are pinned; it does not establish
population validation.

Proposed module paths follow the `us/statutes/42/415/a.yaml` convention
already recorded in this repository. They are proposed paths, not a claim
that files exist in a remote checkout:

| Proposed module | Corpus authority | Required responsibility |
| --- | --- | --- |
| `us/statutes/42/413/a.yaml` | 42 USC 413(a), 20 CFR 404.140-.146 | Quarterly and annual credits, favorable assignment, exclusions |
| `us/statutes/42/413/b.yaml` | 42 USC 413(b) | 1937 half-year allocation or explicit named refusal |
| `us/statutes/42/413/c.yaml` | 42 USC 413(c) | Simplified pre-1951 rule or explicit named refusal |
| `us/statutes/42/413/d.yaml` | 42 USC 413(d), POMS RS 00301.250, OACT QC | Exact QC increment with NAWI indexing, nearest-ten rounding and prior-year floor |
| `us/statutes/42/414/a.yaml` | 42 USC 414(a), 20 CFR 404.110/.115, POMS RS 00301.105 | Fully insured requirement and result |
| `us/statutes/42/414/b.yaml` | 42 USC 414(b), 20 CFR 404.120, POMS RS 00301.110 | Six-in-thirteen current insurance |
| `us/statutes/42/414/c.yaml` | 42 USC 414(c), POMS RS 00301.102 | Alien criterion or explicit named refusal |
| `us/statutes/42/423/c/1.yaml` | 42 USC 423(c)(1), 416(i)(3), 20 CFR 404.130-.131 | Fully insured plus 20/40, young-worker/subsequent special alternatives, blindness |
| `us/policies/ssa/quarter-of-coverage/1978-2027.yaml` | POMS RS 00301.250 and SSA OACT QC | Pinned published calendar-year QC increments |

The caller supplies birth and event dates, canonical sex where the historical
male rule requires it, blindness, disability periods, and year-keyed covered
earnings or direct QCs. Post-1977 direct QCs are annual counts; pre-1978
direct QCs identify quarters. No year is implicitly zero. Each year has
observed, named convention-filled or unknown provenance. A coverage-end
month stops assignment while elapsed-year and recent-work clocks continue.
A nonempty foreign-totalization input is explicitly refused until encoded.

Required outputs are annual QC ranges, favorable assigned-quarter witnesses,
fully/currently/disability insurance, required counts and decision windows,
DLI or a DLI range, unknown years, convention identifiers and the
`decided_despite_unknowns` flag. Each unsupported configuration must return a
named refusal retained in the shared evaluator denominator. Malformed input
must fail before any coverage refusal. Output and refusal records must bind
the rule revision and input declaration.

## Pasteable review_finding

```json
{
  "review_finding": {
    "kind": "missing_statutory_rule",
    "severity": "blocking_for_differential",
    "citations": ["42 USC 413", "42 USC 414", "42 USC 423(c)(1)", "42 USC 416(i)(3)"],
    "finding": "Insured-status decisions require statutory quarter-of-coverage assignment and fully/currently/disability insured rules that are not pinned in the supplied rulespec-us surface.",
    "requested_change": "Encode the cited provisions with exact arithmetic, explicit support/refusal boundaries, date-based windows, provenance-aware unknown-year bounds and the captured worked cases. Provide immutable rule and corpus identities before enabling an Axiom differential.",
    "evidence": "PolicyEngine/microcosm-dynamics tests/data/track_b/insured_status_sources/manifest.json and insured_status_examples.yaml",
    "acceptance": "All supported captured cases reproduce exactly; source errata remain separate from statutory results; every refusal remains in the denominator; malformed input is not counted; every invariant has a property test and deliberate mutations fail."
  }
}
```

## Companion tests

Expectations must come from the same captures, independently of the Python
implementation. Use `tests/data/track_b/insured_status_examples.yaml` as the
case inventory, preserving its coverage labels. In particular:

- RS 00301.250 and OACT: every shared 1978-2026 QC amount agrees, 2010 and
  2011 each require $1,120; OACT 2027 uses $250 × $72,800.33 / $9,226.48,
  shown as $1,972.59 and rounded to $1,970, above the $1,890 prior amount.
- RS 00301.140 Fred: 35 elapsed quarters, odd count reduced to 34, requiring
  17 QCs. Sam: six QCs in the twelve quarters ending 1984Q2. Mary: six in
  the proper twelve-quarter period qualifies; credits outside that period
  do not; movable 1982 credits may be assigned to 1982Q4.
- RS 00301.148: birth March 9, 1954, 30 total QCs, 14 needed to be fully
  insured in 1990, DLI June 30, 1990 after favorable 1980 reassignment.
  FRA in November 2019 limits DLI to September 30, 2019.
- RS 00301.150 Calvin: six QCs in 1986Q1 are short of the seven required;
  1986Q2 supplies the seventh and insurance begins April 1, 1986.
- RS 00301.320 Jane: $400 covered agricultural wages plus the already
  qualifying $50 nonagricultural quarter yields four QCs, never five.
  RS 00301.230 Henry's $1,500 and .325 John's $1,200 in 2010 each produce
  one annual QC assignable to 2010Q1.
- RS 00301.220: fiscal $12,000 allocates $3,000/$9,000. CFR 404.144's
  $1,200 May-to-May example allocates $700/$500. RS 00301.340's regular
  fiscal example allocates $10,800 equally as four $2,700 amounts.
- RS 00301.340 short-year ambiguity: the source labels $10,900 as SEI
  but prints three $3,600 allocations. Literal already-covered SEI divides
  as $10,900/3. Alternatively, an unstated $10,800 contribution-base
  ceiling for the taxable year beginning in 1973, identified in .345 and
  Act 213(a)(2)(B)(iii), gives exactly three $3,600 allocations if $10,900
  meant net earnings before the ceiling. Execute both readings and seek
  clarification; do not declare a proven arithmetic erratum or silently
  infer the ceiling. Both give three QCs, but allocated earnings differ
  by $100. Public short-taxable-year status remains a named refusal.
- RS 00301.345 fiscal gift examples produce four, five and five QCs across
  the taxable-year span; no calendar year may exceed four. Preserve its
  impossible printed “after 1975 and before 1975” interval as a source
  defect rather than silently inventing its intended fiscal boundary.
- Compare fully-insured requirements against every captured CFR 404.115
  birth-cohort row, including historical male transitions and January 1
  birthdays. The RS 00301.800 HTML lacks the linked exhibit's bytes, so
  request the exhibit capture before claiming a .800 differential.
- Exercise subsequent disability .140/.147 examples with all-or-none freeze
  handling and creditable endpoint quarters. Preserve any source-versus-rule
  discrepancy documented by the Python lane; do not make the compiler
  imitate an erratum to force parity.
- Explicitly refuse unsupported deemed, alien, military/railroad, Medicare,
  earned-basis, old-law and totalization inputs. A coverage refusal is not
  evidence that the published person's legal conclusion was negative.

Properties must establish QC and status monotonicity, DLI monotonicity,
0–4 calendar-year bounds, exact window lengths after exclusions,
disability-implies-fully, deterministic order independence, unknown-year
bound soundness and convention transparency. Require at least eight
one-line mutations, report failing test names and revert every mutation.

## Verbatim captured law

The following paragraphs are copied from the pinned LII text excerpts after
the same documented whitespace and apostrophe normalization as the source
tests. No live source has been consulted. The complete original response
identities remain in each manifest entry's `served_bodies`.

### 42 USC 413

Corpus URL: https://www.law.cornell.edu/uscode/text/42/413. Captured 2026-10-21T13:57:14Z; excerpt SHA-256 `b45a823d4376fbb41f40acf31b5df62284afcdf7373c84491bb08df54abfad44`.

> (a) Definitions For the purposes of this subchapter— (1) The term “quarter”, and the term “ calendar quarter ”, mean a period of three calendar months ending on March 31, June 30, September 30, or December 31. (2) (A) The term “ quarter of coverage ” means— (i) for calendar years before 1978, and subject to the provisions of subparagraph (B), a quarter in which an individual has been paid $50 or more in wages (except wages for agricultural labor paid after 1954) or for which he has been credited (as determined under section 412 of this title ) with $100 or more of self-employment income; and (ii) for calendar years after 1977, and subject to the provisions of subparagraph (B), each portion of the total of the wages paid and the self-employment income credited (pursuant to section 412 of this title ) to an individual in a calendar year which equals the amount required for a quarter of coverage in that calendar year (as determined under subsection (d)), with such quarter of coverage being assigned to a specific calendar quarter in such calendar year only if necessary in the case of any individual who has attained age 62 or died or is under a disability and the requirements for insured status in subsection (a) or (b) of section 414 of this title , the requirements for entitlement to a computation or recomputation of his primary insurance amount, or the requirements of paragraph (3) of section 416(i) of this title would not otherwise be met. (B) Notwithstanding the provisions of subparagraph (A)— (i) no quarter after the quarter in which an individual dies shall be a quarter of coverage , and no quarter any part of which is included in a period of disability (other than the initial quarter and the last quarter of such period) shall be a quarter of coverage ; (ii) if the wages paid to an individual in any calendar year equal $3,000 in the case of a calendar year before 1951, or $3,600 in the case of a calendar year after 1950 and before 1955, or $4,200 in the case of a calendar year after 1954 and before 1959, or $4,800 in the case of a calendar year after 1958 and before 1966, or $6,600 in the case of a calendar year after 1965 and before 1968, or $7,800 in the case of a calendar year after 1967 and before 1972, or $9,000 in the case of the calendar year 1972, or $10,800 in the case of the calendar year 1973, or $13,200 in the case of the calendar year 1974, or an amount equal to the contribution and benefit base (as determined under section 430 of this title ) in the case of any calendar year after 1974 and before 1978 with respect to which such contribution and benefit base is effective, each quarter of such year shall (subject to clauses (i) and (v)) be a quarter of coverage; (iii) if an individual has self-employment income for a taxable year, and if the sum of such income and the wages paid to him during such year equals $3,600 in the case of a taxable year beginning after 1950 and ending before 1955, or $4,200 in the case of a taxable year ending after 1954 and before 1959, or $4,800 in the case of a taxable year ending after 1958 and before 1966, or $6,600 in the case of a taxable year ending after 1965 and before 1968, or $7,800 in the case of a taxable year ending after 1967 and before 1972, or $9,000 in the case of a taxable year beginning after 1971 and before 1973, or $10,800 in the case of a taxable year beginning after 1972 and before 1974, or $13,200 in the case of a taxable year beginning after 1973 and before 1975, or an amount equal to the contribution and benefit base (as determined under section 430 of this title ) which is effective for the calendar year in the case of any taxable year beginning in any calendar year after 1974 and before 1978, each quarter any part of which falls in such year shall (subject to clauses (i) and (v)) be a quarter of coverage; (iv) if an individual is paid wages for agricultural labor in a calendar year after 1954 and before 1978, then, subject to clauses (i) and (v), (I) the last quarter of such year which can be but is not otherwise a quarter of coverage shall be a quarter of coverage if such wages equal or exceed $100 but are less than $200; (II) the last two quarters of such year which can be but are not otherwise quarters of coverage shall be quarters of coverage if such wages equal or exceed $200 but are less than $300; (III) the last three quarters of such year which can be but are not otherwise quarters of coverage shall be quarters of coverage if such wages equal or exceed $300 but are less than $400; and (IV) each quarter of such year which is not otherwise a quarter of coverage shall be a quarter of coverage if such wages are $400 or more; (v) no quarter shall be counted as a quarter of coverage prior to the beginning of such quarter; (vi) not more than one quarter of coverage may be credited to a calendar quarter; and (vii) no more than four quarters of coverage may be credited to any calendar year after 1977. If in the case of an individual who has attained age 62 or died or is under a disability and who has been paid wages for agricultural labor in a calendar year after 1954 and before 1978, the requirements for insured status in subsection (a) or (b) of section 414 of this title , the requirements for entitlement to a computation or recomputation of his primary insurance amount, or the requirements of paragraph (3) of section 416(i) of this title are not met after assignment of quarters of coverage to quarters in such year as provided in clause (iv) of the preceding sentence, but would be met if such quarters of coverage were assigned to different quarters in such year, then such quarters of coverage shall instead be assigned, for purposes only of determining compliance with such requirements, to such different quarters. If, in the case of an individual who did not die prior to January 1, 1955 , and who attained age 62 (if a woman) or age 65 (if a man) or died before July 1, 1957 , the requirements for insured status in section 414(a)(3) of this title are not met because of his having too few quarters of coverage but would be met if his quarters of coverage in the first calendar year in which he had any covered employment had been determined on the basis of the period during which wages were earned rather than on the basis of the period during which wages were paid (any such wages paid that are reallocated on an earned basis shall not be used in determining quarters of coverage for subsequent calendar years), then upon application filed by the individual or his survivors and satisfactory proof of his record of wages earned being furnished by such individual or his survivors, the quarters of coverage in such calendar year may be determined on the basis of the periods during which wages were earned.

> (b) Crediting of wages paid in 1937 With respect to wages paid to an individual in the six-month periods commencing either January 1, 1937 , or July 1, 1937 ; (A) if wages of not less than $100 were paid in any such period, one-half of the total amount thereof shall be deemed to have been paid in each of the calendar quarters in such period; and (B) if wages of less than $100 were paid in any such period, the total amount thereof shall be deemed to have been paid in the latter quarter of such period, except that if in any such period, the individual attained age sixty-five, all of the wages paid in such period shall be deemed to have been paid before such age was attained.

> (c) Alternative method for determining quarters of coverage with respect to wages in period from 1937 to 1950 For purposes of sections 414(a) and 415(d) of this title, an individual shall be deemed to have one quarter of coverage for each $400 of his total wages prior to 1951 (as defined in section 415(d)(1)(C) of this title ), except where such individual is not a fully insured individual on the basis of the number of quarters of coverage so derived plus the number of quarters of coverage derived from the wages and self-employment income credited to such individual for periods after 1950.

> (d) Amount required for a quarter of coverage (1) The amount of wages and self-employment income which an individual must have in order to be credited with a quarter of coverage in any year under subsection (a)(2)(A)(ii) shall be $250 in the calendar year 1978 and the amount determined under paragraph (2) of this subsection for years after 1978. (2) The Commissioner of Social Security shall, on or before November 1 of 1978 and of every year thereafter, determine and publish in the Federal Register the amount of wages and self-employment income which an individual must have in order to be credited with a quarter of coverage in the succeeding calendar year. The amount required for a quarter of coverage shall be the larger of— (A) the amount in effect in the calendar year in which the determination under this subsection is made, or (B) the product of the amount prescribed in paragraph (1) which is required for a quarter of coverage in 1978 and the ratio of the national average wage index (as defined in section 409(k)(1) of this title ) for the calendar year before the year in which the determination under this paragraph is made to the national average wage index (as so defined) for 1976, with such product, if not a multiple of $10, being rounded to the next higher multiple of $10 where such amount is a multiple of $5 but not of $10 and to the nearest multiple of $10 in any other case.

### 42 USC 414

Corpus URL: https://www.law.cornell.edu/uscode/text/42/414. Captured 2026-10-21T13:57:15Z; excerpt SHA-256 `deca2cfea26a61b37b847f4cd23d4820c362b6e5644622d50b9b6ee784b6fc24`.

> (a) “Fully insured individual” defined The term “ fully insured individual ” means any individual who had not less than— (1) one quarter of coverage (whenever acquired) for each calendar year elapsing after 1950 (or, if later, the year in which he attained age 21) and before the year in which he died or (if earlier) the year in which he attained age 62, except that in no case shall an individual be a fully insured individual unless he has at least 6 quarters of coverage; or (2) 40 quarters of coverage; or (3) in the case of an individual who died before 1951, 6 quarters of coverage; not counting as an elapsed year for purposes of paragraph (1) any year any part of which was included in a period of disability (as defined in section 416(i) of this title ), and who satisfies the criterion specified in subsection (c).

> (b) “Currently insured individual” defined The term “ currently insured individual ” means any individual who had not less than six quarters of coverage during the thirteen-quarter period ending with (1) the quarter in which he died, (2) the quarter in which he became entitled to old-age insurance benefits, (3) the quarter in which he became entitled to primary insurance benefits under this subchapter as in effect prior to August 28, 1950 , or (4) in the case of any individual entitled to disability insurance benefits, the quarter in which he most recently became entitled to disability insurance benefits, not counting as part of such thirteen-quarter period any quarter any part of which was included in a period of disability unless such quarter was a quarter of coverage, and who satisfies the criterion specified in subsection (c).

> (c) Criterion described For purposes of subsections (a) and (b), the criterion specified in this subsection is that the individual, if not a United States citizen or national— (1) has been assigned a social security account number that was, at the time of assignment, or at any later time, consistent with the requirements of subclause (I) or (III) of section 405(c)(2)(B)(i) of this title ; or (2) at the time any such quarters of coverage are earned— (A) is described in subparagraph (B) or (D) of section 1101(a)(15) of title 8 , (B) is lawfully admitted temporarily to the United States for business (in the case of an individual described in such subparagraph (B)) or the performance as a crewman (in the case of an individual described in such subparagraph (D)), and (C) the business engaged in or service as a crewman performed is within the scope of the terms of such individual's admission to the United States .

### 42 USC 423 (c)(1)

Corpus URL: https://www.law.cornell.edu/uscode/text/42/423. Captured 2026-10-21T13:57:17Z; excerpt SHA-256 `c0db1ea77f2d66910fa5eb7d2fdb9bd37e2f8b31ffc0a3d8a5298a384e277a61`.

> (c) (1) An individual shall be insured for disability insurance benefits in any month if— (A) he would have been a fully insured individual (as defined in section 414 of this title ) had he attained age 62 and filed application for benefits under section 402(a) of this title on the first day of such month, and (B) (i) he had not less than 20 quarters of coverage during the 40-quarter period which ends with the quarter in which such month occurred, or (ii) if such month ends before the quarter in which he attains (or would attain) age 31, not less than one-half (and not less than 6) of the quarters during the period ending with the quarter in which such month occurred and beginning after he attained the age of 21 were quarters of coverage, or (if the number of quarters in such period is less than 12) not less than 6 of the quarters in the 12-quarter period ending with such quarter were quarters of coverage, or (iii) in the case of an individual (not otherwise insured under clause (i)) who, by reason of section 416(i)(3)(B)(ii) of this title , had a prior period of disability that began during a period before the quarter in which he or she attained age 31, not less than one-half of the quarters beginning after such individual attained age 21 and ending with the quarter in which such month occurs are quarters of coverage, or (if the number of quarters in such period is less than 12) not less than 6 of the quarters in the 12-quarter period ending with such quarter are quarters of coverage; except that the provisions of subparagraph (B) of this paragraph shall not apply in the case of an individual who is blind (within the meaning of “blindness” as defined in section 416(i)(1) of this title ). For purposes of subparagraph (B) of this paragraph, when the number of quarters in any period is an odd number, such number shall be reduced by one, and a quarter shall not be counted as part of any period if any part of such quarter was included in a period of disability unless such quarter was a quarter of coverage.

The companion 416(i)(1)-(3) and (l) capture is `lii_usc_42_416_excerpts.txt`, pinned in the same manifest. It supplies the disability-period definition, statutory-blindness exception and retirement-age cross-reference.
