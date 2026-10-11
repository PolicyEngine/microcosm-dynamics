# Gross-benefit (Track B milestone G) source captures

`manifest.json` records, for every source, its URL, UTC retrieval time,
byte count and SHA-256, plus the POMS transmittal where there is one. The
tests in `tests/test_track_b_gross_benefits.py` recompute every hash and
check that each worked-example figure they use appears verbatim in the
capture.

Three capture formats are used:

- `http_body`: the complete decoded HTTP response body, unmodified. All
  POMS sections (`secure.ssa.gov`) were fetched this way on 2026-09-29,
  except RS 00615.801 and RS 00630.400, fetched at 2026-09-30T00:25:16Z
  for the 403(a)(5) review fix.
- `browser_text`: `www.ssa.gov` answered `curl` with HTTP 403 on
  2026-09-29, so those pages were opened in the Claude desktop in-app
  browser. The file holds the rendered text of the cited passages, each
  checked as a substring of the live page. `served_bodies` records the
  byte count and SHA-256 of the raw response the browser fetched at the
  same time, so a later reader can tell whether the page has changed.
- `http_text_excerpt`: verbatim excerpts of a decoded HTTP body after
  stripping tags and collapsing whitespace. The Legal Information
  Institute's United States Code pages for 42 U.S.C. 402 and 415 are about
  1.1 MB and 0.5 MB, so only the cited paragraphs are kept; `served_bodies`
  records each full body's byte count and SHA-256. The 402(w) excerpts
  were added from a re-fetch whose 402 body matched the pinned SHA-256
  byte for byte.

Section 203 of the Act is not duplicated here: R1 captured it in full
(`../ret_sources/ssa_act_203.html`), and the manifest points to that file.

| Source | Used for |
| --- | --- |
| POMS RS 00605.900, .910 | Bend points and the family-maximum chart, every year 1979-2026 |
| POMS RS 00615.005, .101, .201, .301 | Exact-fraction reductions and their rounding |
| POMS RS 00615.020, .240, .250, .260, .694 | Dual-entitlement methods (A then B, B then A, DIB) and delayed credits |
| POMS RS 00615.210, .754, .756 | Reduction for the maximum, then for age |
| POMS RS 00615.320 | The RIB-LIM |
| POMS RS 00615.680, .682, .684, .730 | Beneficiaries paid outside the maximum |
| POMS RS 00615.692, .695, .710 | Delayed credits and the maximum |
| POMS RS 00615.736, .740, .742 | Maximum formula, disability maximum, pre-1982 rounding |
| POMS RS 00615.752, .766, .768 | Totals before adjustment, deductions, the Parisi rule |
| POMS RS 00615.801, RS 00630.400 | Saving clauses: the 1972 Family Payment Saving Clause, whose conditions match 403(a)(5), and how long a saving clause stays in effect |
| SSA OACT family-maximum pages | 2026 bend-point determination; the disability maximum |
| Social Security Bulletin 75(3) | Worked family tables; DI maximum rounding |
| Social Security Act 202, 215 (excerpts) | Benefit shares, entitlement limits, 402(k)(3), 402(q), 215(a)(1)(B)(iii), 215(g), 215(i) |
| 42 U.S.C. 402, 415 (LII excerpts) | Independently entitled divorced spouses (402(b)(4)(A), (c)(4)(A)); no age reduction with a child in care (402(q)(5)(A)); delayed-credit months from full retirement age to 70 and the credit rate by eligibility year (402(w)(2), (w)(6)); COLAs from the eligibility year (415(i)(2)(A)(ii)-(iii)) |

## A source erratum

RS 00605.910 prints `899.52` as the 1981 constant for PIAs above the third
bend point. The statute gives `731.40 + 134% x (508 - 390) = 889.52`, and
RS 00615.736's 1981 example uses the same `405.00` first segment. The test
records the published figure and the statutory one side by side.

These captures establish statutory conformance for worked examples only.
They admit no population, behavioral or forecast claim.
