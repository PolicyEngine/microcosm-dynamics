# Retirement earnings test ledger (Track B R2 part a) source captures

Verification class: **statutory conformance**. These captures establish RET
mechanics for invented records and SSA's published worked examples. They
admit no population, behavioral or forecast claim.

`manifest.json` folds the orchestrator's two 2026-10-11 capture logs into
the established Track B schema. It records each URL, UTC retrieval time,
byte count and SHA-256, plus each POMS transmittal and page date. The Act
203 capture remains in R1's `../ret_sources/` folder and is not duplicated.
Tests recompute every capture hash and check every quoted rule and example
figure against its capture. Every listed source has an explicit rule or
example quote in `tests/test_track_b_ret_ledger_sources.py`.

Three capture formats are used:

- `http_body`: unmodified complete response bodies, including the eCFR
  XML for 20 CFR part 404 subpart E as of 2026-10-07.
- `browser_fetch_body`: complete response bodies captured by the
  orchestrator in the Claude desktop browser when www.ssa.gov refused
  curl. The original capture notes describe browser hashing, transfer
  and local verification.
- `pdf_text`: verbatim passages extracted from the captured Publication
  05-10069 with `pdftotext -layout`. `served_bodies` pins that retained PDF.
  The helper extracts the PDF at test runtime if the command is available;
  the text excerpt is a portability fallback when it is unavailable.

| Source | Used for |
| --- | --- |
| Act 203(b), (f), (h) | Deductions, exempt earnings, reporting; R1 capture |
| RS 02501.001, .021, .025 | RET coverage, FRA, exempt amounts and charts |
| RS 02501.030, .070, .075 | Grace-year history, NSMs and fiscal-year refusal |
| RS 02501.080 | Exact rates, excess floor, FRA-year wage/NESE examples |
| RS 02501.095, .100, .105, .110 | Record order, full provisional suspensions, estimates, exact partial checks |
| RS 02501.120, .125 | Prorated/deferred suspension refusal and crediting scope |
| RS 02501.130, .140 | Deemed non-entitlement and deemed entitlement |
| RS 02501.145, .150 | Two-record excess refusal |
| RS 02501.155, .160 | Part-b deduction-before-reduction refusal; separate households |
| GN 02603.010, .020, .040, .045, .050, .055, .060 | Part-b readjustment boundary, events, formulas, examples and WC/PDB offset boundary |
| GN 02603.075, .090, .100 | Facility-of-payment historical scope and household boundary |
| RS 02510.001, .005, .015, .026 | Current-year estimates versus closed-year reports and enforcement |
| RS 02505.005, .065 | Caller-supplied countable wages and substantial-services flag |
| 20 CFR 404 subpart E | Monthly chart, charging and grace rules; .435 and .439-.441 examples |
| Publication 05-10069 (2026) | Provisional/final repayments, annual table, October retirement special rule |
| Receiving Benefits While Working | $800 benefit, lower and FRA-year deductions |
| Special Earnings Limit Rule | John Smith's July-September payments and October-December work |

## Source findings

RS 02501.080B.2.d describes NESE in 2000 with FRA in June, but prints
`4/99 and 5/99` and an exempt amount of `$15,500`. R1 and both .025's
chart and 20 CFR 404.430 give $17,000 for the 2000 higher exempt amount.
The published countable NESE of $9,776 is reproducible; it stays below
either exempt amount, so the published no-deduction result is unchanged.

20 CFR 404.440 describes a $150 family maximum, a $25 deduction, and $125
remaining, while its displayed dime rates total $149.80. A ledger operating
on the displayed dime rates retains $124.80 after the $25 deduction. Both
paths reproduce the published whole-dollar checks of $75/$16/$16/$16;
the 20-cent difference is pinned explicitly, never hidden by an adjustment.

The 2000/2001 higher monthly chart amounts ($1,417/$2,084) are ceilings
of one twelfth of the annual figures ($17,000/$25,000), while .025B.2
and 20 CFR 404.430(a)(1) say one twelfth. The ledger documents and tests
its reading separately from the source capture.

RS 02501.110B.2 and 20 CFR 404.440 require stopping reapportionment
when excess totals less than $1. This is a substantive exception to
exact conservation of the partial pool and is documented by the ledger.
