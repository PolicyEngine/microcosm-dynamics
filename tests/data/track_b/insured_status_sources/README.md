# Insured-status source captures

Verification class: statutory conformance. These public statutory sources
support invented cases and published examples only. They admit no
population, behavioral or forecast claim.

`manifest.json` pins all 45 captures with their URL, UTC retrieval
time, byte count, SHA-256 and capture format. POMS entries additionally
retain the exact transmittal and page date. The staging log was removed
only after all original byte counts and hashes were verified. The source
tests recompute every retained capture's hash and verify a specific rule
or documentary-purpose quote from every capture. The example registry at
`../insured_status_examples.yaml` checks every published figure against
its source and distinguishes computations, refusals, errata and unavailable
attachments.

The capture formats follow the gross-benefit manifest, with one addition:

- `http_body`: complete decoded HTTP response, unchanged. This includes
  all 37 POMS sections, their table of contents and eCFR subpart B as of
  2026-10-07.
- `browser_text`: staged OACT quarter-of-coverage page text; `served_bodies`
  records the original response identity. Its chart includes 2027.
- `http_text_excerpt`: relevant paragraphs of staged LII bodies, after
  stripping tags, decoding entities, collapsing whitespace and
  straightening apostrophes. Each entry retains the original complete
  response's byte count and hash under `served_bodies`. Excerpts retain
  42 USC 413(a)-(d), 414(a)-(c), 416(i)(1)-(3) and (l), and 423(c)(1).
  No replacement response was fetched.
- `pdf_text`: the RS 00301.800 exhibit's text, extracted from its PDF with
  pdftotext 26.09.0 (`-layout -enc UTF-8`) and kept unchanged.
  `served_bodies` pins the PDF and both GIF renderings of the same table
  (fetched 2026-10-23 from the POMS image store).

| Source | Use |
| --- | --- |
| RS 00301.000, .101 | Source inventory and insured-status overview |
| RS 00301.102 | Alien-worker SSPA requirement; eight cases and one alternative scenario, inventoried with the unsupported adjudicative surface |
| RS 00301.105-.107 | Fully insured and deemed nonprofit status; deemed status refusal |
| RS 00301.110 | Six QCs in a 13-quarter window |
| RS 00301.120, .122, .130-.132 | Disability 20/40, freeze preservation and exclusions, railroad/military refusal |
| RS 00301.140, .147-.150 | Young-worker special status, subsequent-period refusal, DLI, blindness and linked worksheet inventory |
| RS 00301.160-.161 | Medicare government-credit and premium-reduction refusal boundaries |
| RS 00301.200-.250 | Annual QCs, flexible assignment, exclusions, fiscal SE allocation and every 1978-2026 increment |
| RS 00301.301-.350 | Quarterly wages, agriculture, calendar/fiscal self-employment and maximum-earnings gift QCs; railroad and simplified-method boundaries |
| RS 00301.470, .475, .480, .600 | Deemed veterans, earned-basis wages, pre-1956 alternative test and vow-of-poverty refusals |
| RS 00301.800 and its exhibit | Exhibit shell, plus the exhibit's 38-row cohort table, checked row by row |
| 20 CFR 404 subpart B | Statutory rules, worked examples and the 404.115 cohort chart |
| 42 USC 413, 414, 416, 423 | Act 213, 214, 216(i)/(l), 223(c)(1) |
| SSA OACT QC page | Independent 1978-2027 chart and 2027 determination |

The formula differential uses the already pinned R1 NAWI capture at
`../ret_sources/ssa_nawi_history.html` and its `manifest.json`, together
with `../ret_history.json`. Its decimal values are independently checked
against that capture. Exact rational arithmetic reproduces every QC
amount computable from the bundle, 1979-2026; no numerical tolerance is
needed. The 2027 determination uses the OACT capture's 2025 NAWI. POMS and
OACT agree on all 49 shared years, including POMS's joint 2010-2011 row.

## Source limitations and findings

RS 00301.800 links to two GIF images and one PDF of its exhibit. The PDF's
text is captured as `pdf_text`, and all three bodies are pinned by hash.
Every exhibit row is compared, as is every row of CFR 404.115's cohort
chart. The PDF's footnote misprints the male age-65 cohort as "born before
1/2/31"; the GIF rendering, the exhibit's own table and 20 CFR 404.132(b)
say January 2, 1913. RS 00301.149 only points to the SSA-1164 worksheet;
no worksheet reproduction is claimed.

RS 00301.340's short-year example states $10,900 of self-employment
income but allocates $3,600 to each of three quarters, totaling $10,800.
There are two readings. Taking the amount literally as already covered
SEI gives $10,900 / 3 per quarter. An unstated contribution-base ceiling
could explain the printed allocation if $10,900 instead means net
earnings before the ceiling: RS 00301.345 and Act 213(a)(2)(B)(iii) identify
$10,800 for a taxable year beginning in 1973, and $10,800 / 3 = $3,600.
The tests execute both readings. The capture does not state that ceiling
step, so this is an unresolved source assumption rather than a proven
arithmetic erratum. Both readings give three QCs; the allocated earnings
differ by $100 in total. The private allocation helper accepts already
covered SEI, and the public API continues to refuse short taxable years.

RS 00301.345 prints the impossible taxable-year range “after 1975 and
before 1975” for its $14,100 SEI gift-QC bracket. Its ordinary wage table
unambiguously gives $14,100 for calendar year 1975. No fiscal-year
interpretation is inferred from that typo.

RS 00301.102 example 4 states both May 12 and May 14, 2004 as the SSN
issuance date. Both are after the January 1, 2004 threshold. The registry
preserves both printed dates; alien-worker adjudication remains refused.
Examples 2, 5, 6 and 7 expressly say the worker never received an SSN.
The public declaration represents this with `ssn_never_assigned=True` and
returns the named alien-worker refusal, retained in the denominator. It
does not mistake this valid unsupported fact for a missing required date.

RS 00301.120 distinguishes onset/freeze protection from the later DIB
waiting period. A person-month insured-status query does not itself
adjudicate an application, establish a freeze or determine cash entitlement.

The registry separates helper arithmetic from public support: the fiscal
and short-tax-year allocation examples execute private allocation helpers,
while the public insured-status declaration refuses those special taxable
years until the caller supplies calendar-year credited earnings.

Three disability examples have source-versus-rule differences pinned
beside the printed figures. RS 00301.140 example 6 excludes qualifying
endpoint quarters and prints 18 elapsed quarters/9 required QCs; retaining
those endpoints gives 20/10, still insured. Example 9 prints a denial
under a freeze, but disregarding the whole freeze as CFR 404.130(f)
requires when advantageous gives 20 QCs in 40 quarters and insurance.
RS 00301.147 example 3 prints 33 elapsed/16 required/8 available; flexible
assignment of the 1978 annual credit to the final disability quarter gives
34/17/9, still not insured. These differences need explicit review, and
are not counted as exact reproductions of the printed figures.

RS 00301.147 example 2 says the person “requires and has 16” QCs. The
record contains 18; its statement that two additional QCs would meet 20/40
confirms 18. The minimum requirement and insured conclusion reproduce.
