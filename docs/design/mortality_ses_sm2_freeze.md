# SM2 freeze: sources, mappings, joint route, paths and conformance

*Design record, 1 November 2026, branch `mgf-sm2-freeze-20261101`, written
from `origin/master` `1808285925a069143047ae7e7bb2412012db0ad7` by the
mortality, groups and financing lane's SM2 freeze job (Subfleet build,
Claude Code, Opus 5.5).*

*Revised 3 November 2026 by the same lane's fix round 1 (Subfleet build,
Claude Code, Opus 5.5), which answers independent review r1 and changed
only this file; §13.6 records what that round read and fetched.*

*Revised 7 November 2026 by fix round 2 (Subfleet build, Codex, GPT-6).
This round answers review r2; §13.7 records its reads and checks.*

## 1. Status and authority

**This record freezes SM2 under section 5.1 of the lane design**
(`docs/design/mortality_groups_financing.md`), which requires the record
to freeze source hashes, module versions, seeds, populations, estimands,
tolerances and alternatives before anyone computes a real-data outcome. **It is not a
registration on #42, and it claims no blind status.** The job that wrote
it read every source it freezes, so it and this file count as exposed to
those sources; nothing here feeds a blind role.

- **Verification class.** External-target conformance, labeled
  **"calibrated, not validated"** (design section 3.2): SM2 admits that
  the fitted relative risks reproduce the targets the fit used,
  never that the model predicts. SM2 claims **no prospective prediction
  origin and no unused holdout** (S0.1 section 2.4). The held-out test of
  the gradient is SM3.
- **Authority.** Max approved the lane design, with its methodology, on
  23 October 2026 (decision d1922). S0.1's audit
  (`docs/design/s0_1_source_audit.md`, #588, merged 1 November 2026) is
  this record's input; its section 2 is SM2's record. Its header says a
  review and the gate's registration "confirm or amend" each
  **[proposed]** item before anyone computes an outcome, and "may tighten or
  rescope it but never loosen it". This record tightens or rescopes in
  the places section 2's table names. Fix round 1 weakened the frozen
  disagreement consequence; this round restores it throughout (§10).
  The operative rules here loosen no frozen requirement.
- **Rulings that bind this record, unamended.**
  - **Q4:** within each single age × sex × year cell, SM1's normalizer
    scales relative risks to the baseline's expected deaths
    (`src/populace_dynamics/mortality_ses/normalizer.py:328–382`).
  - **Q5:** lifetime earnings is the primary dimension; education and race
    and Hispanic origin are further dimensions of the same model.
  - **Q6:** the gradient holds at its last observed level as the primary
    path; a widening path is a registered alternative.
  - **Q11:** SM owns death alignment.
- **What it computes.** Nothing. This record states no fitted
  coefficient, no contrast between categories, no life expectancy and no
  comparison between sources' gradients, and it prints no source table
  value. It names tables, pages, age bands, years and categories only.
  Every number in it is a year, an age, a page or line, a count of table
  cells, targets, files, PDF objects or drawing operators, a file's byte
  size or hash, a code from a codebook, a tolerance the design or S0.1
  sets, a rule, constant or seed this record sets, or a constant it
  derives from those (the Bonferroni critical values and the widening
  they imply).
- **Data.** Neither the freeze job nor either fix round opened a PSID, HRS,
  SIPP, NHIS or ACS microdata file, and none computed anything on real
  data. PSID use follows the project's data-access record. This record
  uses and compares no DYNASIM, Urban Institute or PWBM material, which
  reaches these gates only through a validation lane (S0.1 scope). CBO
  publication 49659 stays closed; its methods count as open until a
  validation lane supplies a bounded definitions-only extract.
- **Current eligibility, before any fit.** OACT random variation and LMF
  perturbation remain open. Both propagate through JR-C to every derived
  earnings and race e65 member (§9.3); lifetime earnings, race and
  Hispanic origin, and SM2 cannot pass until the components each member
  needs close. Education keeps a separate reconstruction-conformance
  status subject to the other requirements; option (b) leaves its 85+
  targets inconclusive too (§4.5). Numeric intervals omit and name both
  components, yet those omissions affect verdicts through dependencies.
  Section 9.7 counts component eligibility with other issues resolved;
  it reports no real-data verdicts. A post-outcome closure requires a new
  registered version preserving the first attempt (§9.3, §10).
- **Markers.** **[frozen here]** marks a decision this record makes.
  **[frozen, S0.1 §x]** keeps a decision S0.1 already froze, with its
  pointer. **[open]** marks an item this record leaves unsettled and names
  what settles it.

## 2. Item table

S0.1's section 2 runs from line 324 to line 707 of the audit at
`18082859`. This command recounts its bracketed markers that contain
"proposed" or "open":

```
sed -n '324,707p' docs/design/s0_1_source_audit.md \
  | grep -oE '\[[^]]*(proposed|open)[^]]*\]' | wc -l
```

It returns **20**. The rows S2-01 to S2-20 below take them in the audit's
order. A word search over the same lines
(`awk 'NR>=324 && NR<=707 && /(^|[^a-z])(open|proposed|pending|unsettled)([^a-z]|$)/'`)
finds five more lines that call something open or proposed without a
bracketed marker; rows S2-21 to S2-25 cover them, so the table has
**25 rows**. Where a row says "tightened" or "rescoped", the change is
narrower than S0.1's proposal or adds a requirement; no row loosens one.

| Row | Audit line | S0.1 item | Resolution | Where | State |
|---|---|---|---|---|---|
| S2-01 | 424 | **[proposed]** mapping assumption: OACT rate ratios used directly as annual-q multipliers, reported with the dynamic-AIME versus frozen-rank distinction and the beneficiary population difference | Confirmed and tightened: adds Study 129's exposure convention (deaths get a full year of exposure, which makes each published rate an initial-exposure estimate of an annual probability, p. 5 and Appendix B pp. 13–14), the age-basis mapping, and three named mapping assumptions (M-E2 to M-E4) that every report carries | §4.1 | frozen here |
| S2-02 | 440 | **[open]** availability of earlier NCHS education editions | Settled by the NVSR listing and twelve earlier *Deaths: Final Data* reports: 2010–2017 cover reporting states only (31 rising to 49 states plus DC); 2018–2020 are national in the internet tables I–7 and I–19; 2021–2022 are national in printed Table 14 and Table VIII; the listing of 1 November 2026 holds no edition for 2023. The fit uses 2018–2022; 2010–2017 form a labeled sensitivity. A fitted year whose layout fails counts as unavailable; its members remain inconclusive in the family and block admission; the latest education source stays 2022 (§10) | §3.2 | frozen here |
| S2-03 | 474 | **[open]** harmonization of earlier NHIS years | Rescoped to NHIS 2009–2018 sample adults. The 2009, 2016 and 2018 layouts carry `EDUC1`, `HISPAN_I`, `RACERPI2`, `AGE_P`, `SEX`, `SRVY_YR`, `INTV_QRT` and `HHX`/`FMX`/`FPX` with identical code lists; the design variables are `STRAT_P`/`PSU_P` in 2009 and `PSTRAT`/`PPSU` in 2016 and 2018. Year-qualified family/person keys and a nesting/singleton stop tighten survey handling (§9.3). The fit job checks each intervening year's layout against these names and code lists before use; a year that fails leaves the pool, labeled "NHIS year dropped: layout", and if no year passes, `SOURCE_UNAVAILABLE` (ii) applies (fix round 1) | §3.4, §9.3 | frozen here (window and variables); intervening layouts checked by the fit job, with the failure outcome frozen |
| S2-04 | 481 | **[open]** a three-dimension joint gradient conditional on lifetime earnings | Resolved by the joint route: joint marginal calibration on a public reference population, with the earnings–education–race dependence taken from a stated proxy. Support and rank checks tighten the route before any residual inspection (§6.3). A disagreement removes competing NCHS/NHIS sources from fitted roles, leaving JR-C without education/race targets and stopping it under `SOURCE_UNAVAILABLE` (§10). The dependence itself stays unidentified in public data, and §6.6 says so. Where the fit applies the proxy's dependence outside its estimation sample, this record names the copy assumption M-J1, with sensitivity JR-C-IND (§6.5, §6.6) | §6 | frozen here (route); the dependence stays unidentified and named |
| S2-05 | 511 | **[open mapping]** Cristia's odds ratios | Frozen: predicted probabilities on a named reference population, then ratios to `q3`'s probability. Cristia enters only as a sensitivity and a source reported beside the fit; no log odds ratio enters as a log relative risk | §4.4 | frozen here |
| S2-06 | 520 | **[proposed]** CBO 41681 as context only | Confirmed. It supplies the reason the widening alternative leaves race and Hispanic origin flat (pp. 1–2), with p. 1's qualifier that the black–white gap held for men and narrowed for women, and no coefficient or target | §3.1, §7.4 | frozen here |
| S2-07 | 538 | **[proposed schema]** dimensions, columns, categories, references and unclassified treatment | Confirmed against `mortality_ses/specification.py`; tightened to one unclassified string per dimension, a fixed category order, and a crosswalk per source. `R_ref`'s persons under 25 hold the reference categories by rule, labeled `reference_below_25` (§6.2, §8.1). The ACS crosswalk maps every `SCHL`, `HISP` and `RAC1P` code in the 2010–2019 and 2021–2024 dictionaries; fix round 2 also confirms 2020's experimental code lists (§8.2). NHIS `HISPAN_I` 00–11 map to `hispanic`, following S0.1's frozen reading, with 10 and 11 unclassified in X-R1 | §8 | frozen here (2020 code-list item closed in fix round 2) |
| S2-08 | 564 | **[proposed loader]** OACT contrasts `log(r_q) − log(r_q3)`, band expansion, a source-year matrix that says what happens before a band first appears | Confirmed; tightened with the band-backcast rule, the figure-year rule and two independent table transcriptions | §3.1, §4.1, §5 | frozen here |
| S2-09 | 570 | **[open]** earnings ages below 62 and 90–120 | Frozen: the 62–64 coefficient holds down to age 25 and the age-25 value below; the 85–89 coefficient holds up to 120; five registered sensitivities. `R_ref` holds everyone under 25 at the reference categories, so the values below 25 reach no one in the fit (§6.2) | §5, §6.2 | frozen here |
| S2-10 | 579 | **[open]** terminal 100+ rule and any unsupported other-group coefficient | Frozen: race contrasts at 100–120 hold the age-99 contrast, and the fit reads no contrast from the 100+ interval; the e65 targets read that interval's `Tx` and `lx` for NCHS's closing only (§9.2); `other_non_hispanic` uses NHIS–LMF where identified. Fix round 2 narrows that input: its unidentified 85+ targets cannot pass (§4.5). NCHS's AIAN and Asian tables remain beside the fit as a partial group | §4.3, §5, §9.2 | frozen here |
| S2-11 | 587 | **[open]** extraction and digitization of the 2022 gradient, its uncertainty, complete coverage | Frozen: vector extraction of Study 129 Figures 7–12, validated against Tables 7–12 at every table year, with a digitization half-width the validation sets; complete tables at every knot | §7.1–7.3 | frozen here |
| S2-12 | 591 | **[open]** widening `CoefficientPath`: slope, origin, ages, caps; knot years and synchronization | Frozen: origin 2024, slopes from a frozen estimator on OACT's pre-pandemic annual figures, caps of 30 years and a 1.5 multiplier, race held flat; annual knots 2010–2024 with one synchronization rule | §7.4–7.5 | frozen here |
| S2-13 | 602 | **[proposed]** `unclassified_rule="reference"` for SM3's overall denominator | Confirmed for SM3; `refuse` for conformance runs and for any projection until the frame carries the attributes. On `R_ref`, `refuse` applies after the under-25 rule and the ACS crosswalk, which map every code the dictionaries read list (§6.2, §8.2) | §8.3 | frozen here |
| S2-14 | 606 | **[open: identification]** marginal contrasts do not determine mutually adjusted coefficients; freeze a joint route and its reference distribution | Five candidate routes and one unavailable route; primary JR-C subject to the identification and disagreement stops. A disagreement leaves competing sources only as sensitivities, with no fitted substitute (§10). JR-A (plain addition, labeled), JR-B, JR-D and JR-E as sensitivities. NHIS targets compare as age-standardized hazard ratios on `R_ref(t)`'s single-age population, under named assumption M-H1 (§4, §4.5). Support and rank checks now precede conformance residual inspection, tightening the proposal; unidentified 85+ NHIS members cannot pass (§4.5, §6.3). The ordered logit fits once per knot year and sex on that year's ACS, and again inside every replicate, with a frozen optimizer, convergence rule and tie rule (§6.2). The ACS income item passes a frozen acceptance rule, and JR-C-W covers the proxy's weakness for women (§6.2, §6.5) | §4, §6 | frozen here |
| S2-15 | 629 | **[open]** exact release dates of any earlier NHIS cohort used | Left open. The linked-mortality `.dat` files carry the listing date 26 April 2022; each NHIS year's release date settles from that year's survey description, which the fit job records. Nothing in SM2 depends on it, because SM2 claims no prospective origin | §3.4 | left open; settled by the fit job's per-year release ledger |
| S2-16 | 641 | **[frozen tolerance; proposed operationalization]** e65 target from source ratios on one baseline, with a fixed reference population, marginalization and tail rule | Frozen; the 0.1-year limit stays. Fix round 2 tightens the operationalization: it converts the other-group source hazard before baseline rescaling, names the open-interval central-rate assumption, and adds the tail extraction fields. Corrected in fix round 1 to keep NCHS's age and closing conventions, which S0.1 requires (audit lines 647–648) and the first draft dropped: the race and Hispanic-origin targets close NCHS's "100 and older" interval as NCHS does, and the model side keeps the repository's closing, so a mismatch in the tail reaches the test. The earnings targets keep the fixed tail rule S0.1 asks of OACT (audit lines 643–646) | §9.2 | frozen here (operationalization); tolerance frozen, S0.1 §2.5 |
| S2-17 | 649 | **[open]** whether the different source populations and baselines can satisfy the targets together | This record freezes the procedure: one joint calibration per knot on one reference population, and a named failure when it cannot reproduce every target. Whether it can is an outcome, so this record does not settle it | §6.3, §9 | left open; settled by the fit under §9's rule |
| S2-18 | 659 | **[open until the loader plan is frozen]** the critical family's integer size and which joint-survey targets it holds | Frozen and tightened: **6,884** targets, itemized and machine-counted in §9.7; missing members never leave the conjunction | §9.4 | frozen here |
| S2-19 | 677 | **[proposed named procedure]** `SM2_SOURCE_RECONSTRUCTION_AND_CLUSTER_BOOTSTRAP` | Filled in step by step; tightened with endpoint validity and error checks, unresolved-age handling, rank checks and component dependencies, and restoration of the frozen disagreement consequence in fix round 2 | §9 | frozen here |
| S2-20 | 688 | **[proposed suppression]** at least 100 unweighted persons per published microdata subgroup | Confirmed and tightened: also at least 20 deaths in any published death-based cell, and the rule applies to ACS as well as NHIS aggregates | §11.5 | frozen here |
| S2-21 | 353 | Unmarked: CBO 49659's "safely bounded definitions remain open" | Left open as the brief requires; SM2 uses no part of 49659 | §3.1 | left open; settled by a validation lane's definitions-only extract |
| S2-22 | 523 | Unmarked: "CBO 49659's mixed-source methods remain open pending a safely bounded definitions-only extract" | Same item as S2-21 | §3.1 | left open; as S2-21 |
| S2-23 | 588 | Unmarked: "A 2020 table-only path is a proposed registered sensitivity" | Confirmed as sensitivity P-TABLE; it cannot become primary without amending Q6 | §7.3 | frozen here |
| S2-24 | 669 | Unmarked: a source that does not publish the uncertainty a target needs leaves that item "open or inconclusive" | Applied component by component and residual by residual: all 150 earnings e65 and 120 race e65 members need both OACT random variation and LMF perturbation through the joint calibration, absent a reviewed invariance proof. A point failure still fails. Same-target successful-refit contrasts retain reconstruction verdicts. Public LMF perturbation enters no numeric bound but reaches verdicts through dependencies. Both omitted components label intervals handed on; the fit runs and publishes supported results. A closure after outcomes requires a new registered version, preserving the first attempt | §1, §9.3–§9.7, §10 | left open; source-published uncertainty, sufficient deaths/exposure, or reviewed residual-specific invariance, through a recorded amendment; restricted-use LMF first needs its exclusion amended |
| S2-25 | 698 | Unmarked: "`SOURCE_UNAVAILABLE` / open identification applies to the complete modern three-dimension joint source and missing source-age mappings" | Tightened: support/rank, valid dates, family nesting and singleton checks block unsupported fits; every missing NCHS member remains in the family, and a missing last-observed source blocks its dimension and SM2 | §10 | frozen here |

**Counts.** Of the 25 rows, this record freezes 20 procedures/resolutions and leaves 5 items open, each
with what settles it (S2-15, S2-17, S2-21, S2-22, S2-24); none goes to Max.
The frozen option (b) procedure explicitly leaves the eight NHIS 85+
members unidentified; the row-state count does not count them as closed.
S2-24's open components prevent lifetime earnings, race and Hispanic
origin, and SM2 from passing until their required dependencies close.
Education has a separate reconstruction status subject to other limits,
including §4.5's unidentified 85+ members. The fit reports every dimension's
status (§9.5). S2-02 and S2-03 retain fit-job checks for the NCHS education
and intervening NHIS layouts, with failure outcomes frozen here; S2-07's
2020 ACS code-list item closes in this round. Section 12 holds two rules for cases outside this table.

## 3. Source-year matrix

This job read every source below at the SHA-256 that section 13 lists.
"Fit" means the source supplies a target the joint calibration
reproduces; "beside" means the record reports the source next to the fit
and fits nothing to it; "context" means it informs a reason and supplies no
number;
"reference" means it supplies the reference population, not a target.
S0.1's design line requires at least one source not used in fitting,
reported beside the fit; this record names one or more for each dimension
(§3.6). **[frozen here]** for every role and year rule in this section.

### 3.1 Lifetime earnings

| Source | Table or figure, PDF page | Categories | Sex | Age bands | Years published | Role |
|---|---|---|---|---|---|---|
| OACT Actuarial Study No. 129 (December 2024, Figure 6 corrected June 2025) | Tables 7–12, relative mortality ratios (RMRs), pp. 27–32 (PDF page equals printed page) | Lowest, 2nd, 3rd, 4th and Highest AIME quintile, Total, and a share row ("Percentages represent the share of workers in that sex and age group") | Male, female | 62–64, 65–69, 70–74, 75–79, 80–84, 85–89 | 1995, 2000, 2005, 2010, 2015, 2020 | Fit at 2010, 2015 and 2020 |
| Study 129 | Figures 7–12, RMRs by band, pp. 33–38, one figure per band with a men's and a women's panel and five series | Five quintiles | Male, female | One band per figure | Each calendar year 1995–2022 | Fit at 2011–2014, 2016–2019, 2021–2022 (fully supported bands only) |
| Study 129 | Tables 1–6, death rates, pp. 15–20 | As Tables 7–12 | Male, female | As Tables 7–12 | As Tables 7–12 | Cross-check only (§9.1): ratios of printed rates must agree with printed RMRs within both rounding intervals |
| Study 129 | Figures 1–6, death rates, pp. 21–26 | Five quintiles | Male, female | One band per figure | 1995–2022 | Not used |
| OACT Actuarial Study No. 124 (April 2018) | Tables 4–8, RMRs by AIME quintile, pp. 11–15; Tables 9–13, hypothetical-worker intervals, pp. 21–25 | Five quintiles and Total; five intervals | Male, female | 62–64 to 80–84 and a Total column | 1995, 2000, 2005, 2010, 2015 | Beside (vintage revision of the same quantity on the June 2017 MBR, birth cohorts 1930 and later, p. 6) |
| Cristia (2007), CBO Working Paper 2007-11 | Tables 3–4, age-standardized mortality ratios, PDF pp. 38–39; Tables 5–6, logistic regressions, PDF pp. 40–41 | Lifetime-earnings quintiles (own and household); race and ethnicity; education; marital status | Men (Tables 3, 5), women (Tables 4, 6) | 35–75, 35–49, 50–64, 65–75 | Person-years 1983–2003 | Beside, and sensitivities JR-D (§6) and T-E2 (§5) |
| CBO publication 41681 (17 April 2008) | pp. 1–3, Figures 1–2 | Synthesis | — | — | — | Context (§7.4 reason) |
| CBO publication 49659 (7 November 2014) | — | — | — | — | — | Closed; methods open until a validation lane supplies a bounded definitions-only extract |
| OACT presentation, Tiffany Bosley, 14 January 2025 | Slides 1, 3, 23 | — | — | — | — | Identity of the January 2025 update only (S0.1 §2.1) |

**Bands and years in Study 129.** Each table prints "-" for the bands it
does not report. The study takes only workers reaching 62 in 1993 or later
(p. 6; notes under Tables 1–12), so a band `[a1, a2]` holds only such
workers at every one of its ages from year `1993 + (a2 − 62)`, which this
record calls the band's first fully supported year: 62–64 from 1995,
65–69 from 2000, 70–74 from 2005, 75–79 from 2010, 80–84 from 2015 and
85–89 from 2020. The printed "-" cells match that schedule exactly. Study
124's Tables 4–8 print the same pattern through 80–84 in 2015, although
that study takes birth cohorts from 1930 (p. 6).

**Printing.** Tables 7–12 print RMRs to two decimals and the share row to
one decimal; Tables 1–6 print rates to four decimals (counted from the
text layer without reading values: 252 two-decimal and 252 four-decimal
quintile-or-total cells, which equals 21 band-years × 2 sexes × 6 rows).

**Figures as vector content.** Page 34's content stream holds 1,281
line-to and 846 move-to operators and no raster plot image; pages 34–38
list no image object at all, and page 33 lists only 14 small 16 × 16
stencils and one 192 × 2493 ccitt image (`pdfimages -list`). A digitizer can
therefore recover the annual series from path coordinates (§7.2).

**Appendix lettering.** The body text places Tables 7–12 in Appendix E
and Figures 7–12 in Appendix F (pp. 7–9), but the printed headings read
"D. Age Group Death Rate Figures" (p. 21) and "E. Age Group Relative
Mortality Ratios by AIME Quintile Levels" above Figure 7 (p. 33), and
Tables 7–12 carry no letter (p. 27). This record cites tables and figures
by number and page only.

**Before a band first appears.** For a knot year earlier than a band's
first fully supported year, the band's targets take their values from that
first year (`BAND_BACKCAST_HOLD_FIRST`): 80–84 for 2010–2014 from 2015,
and 85–89 for 2010–2019 from 2020. These copies are assumptions, not
published values; they enter no critical-family count as new targets
(§9.4), and §5 registers the alternative, T-B1. The fit records, and never fits, a
figure point plotted in a year before its band's first fully supported
year.

### 3.2 Education

| Data year | Report | Education table, PDF page | Population and SE table, PDF page | Coverage | Role |
|---|---|---|---|---|---|
| 2010 | NVSR 61(4) | Internet tables | Internet tables | 31 reporting states (titles also read "31 reporting states and the District of Columbia") | Sensitivity E-S1 only |
| 2011 | NVSR 63(3) | Internet tables | Internet tables | 33 reporting states | E-S1 |
| 2012 | NVSR 63(9) | Internet tables | Internet tables | 38 reporting states | E-S1 |
| 2013 | NVSR 64(2) | Internet tables | Internet tables | 39 reporting states and DC | E-S1 |
| 2014 | NVSR 65(4) | Internet tables | Internet tables | 43 reporting states (and a DC variant) | E-S1 |
| 2015 | NVSR 66(6) | Internet tables | Internet tables | 46 reporting states | E-S1 |
| 2016 | NVSR 67(5) | Internet tables | Internet tables | 49 reporting states | E-S1 |
| 2017 | NVSR 68(9) | Internet tables | Internet tables | 49 reporting states and DC | E-S1 |
| 2018 | NVSR 69(13) | Internet Table I–7, p. 15 | Internet Table I–19, p. 72 | United States | Fit |
| 2019 | NVSR 70(8) | Internet Table I–7, p. 15 | Internet Table I–19, p. 71 | United States | Fit |
| 2020 | NVSR 72(10) | Internet Table I–7, p. 20 | Internet Table I–19, p. 88 | United States | Fit |
| 2021 | NVSR 73(8) | Table 14, p. 87 | Table VIII, p. 133 | United States | Fit |
| 2022 | NVSR 74(4) | Table 14, p. 86 | Table VIII, p. 133 | United States | Fit |

- **Layout, 2018–2022.** Number of deaths, death rate and age-adjusted
  death rate for ages 25–34, 35–44, 45–54, 55–64 and 25–64, by sex (both,
  male, female) and three education levels: less than high school diploma
  or GED; high school diploma or GED; some college or collegiate degree;
  plus "not stated" in the counts. Rates are per 100,000 population; the
  population tables print each estimate with its standard error. This job
  read the 2018, 2020 and 2022 layouts with values masked and the 2019 and
  2021 titles only; the fit job's loader checks every year's layout. A
  year whose layout does not match this one (bands, sexes, the three
  education levels and the columns) counts as unavailable, as a missing
  file does under `SOURCE_UNAVAILABLE` (vii) (§10); its members stay
  inconclusive in the family, and the dimension and SM2 cannot pass;
  the same rule covers every life-table year in §3.3.
- **Limits stated by the source.** No data below 25 (schooling may be
  incomplete) and none at 65 and over ("reporting quality is poorer at
  older ages"), with completeness the technical notes state (NVSR 74(4)
  p. 127). The
  denominators come from 1-year ACS PUMS adjusted to July 1 resident
  control totals (p. 132), and the rates' standard errors combine Poisson
  variation in deaths with the ACS standard error (Formulas 9 and 10,
  p. 132). The 2020 denominators use the 2020 1-year ACS PUMS (NVSR 72(10)
  internet tables, p. 2).
- **No later edition.** The NVSR listing fetched on 1 November 2026 holds
  no *Deaths: Final Data for 2023*; its latest final-deaths report is NVSR
  74(4) for 2022. The last observed education year is therefore 2022.
- **Why the fit leaves out 2010–2017.** Their populations are the
  reporting states, not the United States, so their denominators and
  composition differ from the reference population (§6). This job did not
  check their category sets and age bands; sensitivity E-S1's loader checks
  them before use, and a year whose categories or bands differ from the
  2018–2022 layout leaves E-S1, labeled.
- **Ages 65 and over and the `some_college`/`college` split.** NCHS
  supplies neither (§4.2). NHIS–LMF supplies both (§3.4).

### 3.3 Race and Hispanic origin

| Data years | Reports | Groups with life tables (each total, male, female) | Table numbers verified in this job |
|---|---|---|---|
| 2010–2017 | NVSR 63(7), 64(11), 65(8), 66(3), 66(4), 67(7), 68(4), 68(7) | Total; white; black; Hispanic; non-Hispanic white; non-Hispanic black (bridged race) | 2010 and 2017: Hispanic Tables 10–12, NH white 13–15, NH black 16–18 |
| 2018 | NVSR 69(12) | Total; Hispanic; NH white; NH black (single race) | Hispanic 4–6, NH white 7–9, NH black 10–12 |
| 2019–2024 | NVSR 70(19), 71(1), 72(12), 74(2), 74(6), 75(5) | Total; Hispanic; NH AIAN; NH Asian; NH black; NH white (single race) | 2019, 2022, 2023, 2024: Hispanic 4–6, NH AIAN 7–9, NH Asian 10–12, NH black 13–15, NH white 16–18 |

- **Layout.** Complete period life tables with single ages 0–99 and an
  open "100 and older" interval; columns `qx`, `lx`, `dx`, `Lx`, `Tx`,
  `ex`; `qx` printed to six decimals and `ex` to one (NVSR 75(5),
  pp. 2, 16–49). In NVSR 74(2) and 75(5) the male and female tables start
  on pp. 16 and 18 (total), 22 and 24 (Hispanic), 28 and 30 (AIAN), 34
  and 36 (Asian), 40 and 42 (black) and 46 and 48 (white).
- **Methods the source states.** Hispanic, NH white and NH black tables
  begin with 2006 data; AIAN and Asian NH tables begin with 2019 data
  (NVSR 75(5) p. 53). Single-race categories under the 1997 standards
  begin with 2018, replacing bridged race (pp. 1–2, 54). Rates carry a
  misclassification adjustment; Medicare data supplement ages 66–99 for
  the total, NH black and NH white tables only, and NCHS models old-age
  mortality for the Hispanic, AIAN and Asian NH tables (pp. 2, 54–55); the
  2008-onward method smooths death rates above about 85, at ages that
  depend on the group (p. 53). A Kannisto logistic model smooths the
  Medicare-blended rates at 85–99 and predicts them at 100–120 (p. 57); a
  Brass relational logit, with the white non-Hispanic age pattern as its
  standard, predicts the older ages of the Hispanic, AIAN and Asian NH
  tables (pp. 59–62). Every table then closes its "100 and older" row with
  `∞q100 = 1.0`, `∞d100 = l100` and `∞L100 = T100`, the sum of the
  extrapolated `Lx` for 100–120 (pp. 61–62).
- **Fit.** Hispanic, NH white and NH black for every knot year 2010–2024
  (bridged race through 2017, single race from 2018, both labeled). The
  2006–2009 tables lie before the first knot, and the fit does not use
  them.
- **The `other_non_hispanic` group.** No NCHS table covers it. AIAN and
  Asian NH tables leave out Native Hawaiian and Pacific Islander,
  multiracial and other people, and exist only from 2019, so a weighted
  average of them is not the full group (S0.1 §2.3). The fit takes this
  group's contrast from NHIS–LMF (§3.4); the record reports the
  AIAN-and-Asian composite for 2019–2024 beside it, labeled "partial
  group".

### 3.4 Public NHIS–LMF

- **Release.** The 2019 public-use linkage: NHIS 1986–2018 interviews,
  mortality follow-up through 31 December 2019 (description p. 1). The
  NCHS FTP listing fetched on 1 November 2026 holds
  `NHIS_<year>_MORT_2019_PUBLIC.dat` for 1986–2018, all dated
  26 April 2022, and no later public linkage. The Linked Mortality Files
  page (revised 7 July 2026) announces follow-up through 31 December 2022
  for NHIS 1986–2021, but only as restricted-use files; they stay
  excluded.
- **Window [frozen here]: sample adults interviewed 2009–2018.** Reasons:
  a single sample-adult universe with eligibility-adjusted weights
  `SA_WGT_NEW` (codebook p. 4); identical `EDUC1`, `HISPAN_I` and
  `RACERPI2` code lists in the 2009, 2016 and 2018 layouts; deaths
  2009–2019, which overlap the fitted years of every other source. From
  2015 only sample adults were linkage-eligible (description p. 2).
- **Variables.** `EDUC1` (person file; 2009 layout p. 265, 2016 p. 296,
  2018 p. 294); `HISPAN_I`, `RACERPI2`, `AGE_P`, `SEX` (sample adult file;
  2009 pp. 7, 8, 10; 2016 pp. 8, 9, 11; 2018 pp. 8, 9, 11); design
  variables `STRAT_P`/`PSU_P` (2009, p. 6) and `PSTRAT`/`PPSU` (2016 and
  2018, p. 6); `MORTSTAT`, `ELIGSTAT` (codebook p. 1), `DODQTR`, `DODYEAR`
  (p. 3), `SA_WGT_NEW` (p. 4); merge by `PUBLICID` (description p. 4).
- **What the public files do not hold.** Ages above 84 at interview
  (`AGE_P` is 85 for every older person), month and year of birth, and the
  flags that show whether NCHS imputed race or ethnicity (2018 survey
  description pp. 25–26); any lifetime-earnings history; deaths after
  2019. Some records carry synthetic follow-up time or cause (description
  p. 1).
- **Roles.** Fit: education contrasts at attained ages 65–74, 75–84 and
  85+, the `college`/`some_college` split at 25–64, and
  `other_non_hispanic` contrasts. Beside: education contrasts at 25–64
  and `hispanic` and `black_non_hispanic` contrasts, next to NCHS's.
- **Release dates of the 2009–2018 NHIS files** stay **[open]** (row
  S2-15); the fit job records each from that year's survey description,
  or "not stated" where a description gives none.

### 3.5 Reference population and baseline

- **Reference population (reference, not a target) [frozen here].** The
  Census Bureau's ACS 1-year PUMS person files for each knot year
  2010–2024, with their person weights and replicate weights. NCHS built
  its 2020 education denominators from the 2020 1-year PUMS (NVSR 72(10)
  internet tables, p. 2), and the fit uses that file too. The Census
  Bureau "did not release its standard 2020 ACS 1-year" PUMS because of
  the pandemic and released the file "with experimental weights and
  replicate weights" (its 2020 PUMS documentation page, §13.6); the fit
  labels the 2020 knot's reference population accordingly and records any
  further note. §6 defines the population built from these files. The
  first freeze job opened no ACS file or documentation. Fix round 1 read
  the ACS data dictionaries for 2010–2019 and 2021–2024, the subject
  definitions for 2010–2024 and the 2024 top-coded-values document
  (§13.6), and opened no ACS microdata; the data files' URLs stay
  unchecked (§11.6).
- **Baseline [frozen, S0.1 §1.1].** OACT's TR 2026 single-age, sex and
  year `q` through the pinned accessor `data/tr2026.death_probability`,
  historical through 2023 and Alternative II from 2024, ages 0–120 with
  age 120 repeating age 119 (S0.1 §1.1 citing
  `baselines/tr2026_intermediate.py:154`). `BaselineYearAwareMortality`
  applies the year-`t` period `q` at the start-of-year age
  `t − 1 − birth_year` (`baselines/base.py:19–28`).

### 3.6 Roles by dimension

| Dimension | Fitted sources | Reported beside, not fitted | Context |
|---|---|---|---|
| Lifetime earnings | Study 129 Tables 7–12 and Figures 7–12 | Study 124 Tables 4–8; Cristia Tables 3–6 | CBO 41681 |
| Education | NCHS 2018–2022 (25–64); NHIS–LMF (65+, split) | NHIS–LMF at 25–64; Cristia Tables 3–6; NCHS 2010–2017 reporting-state tables | CBO 41681 |
| Race and Hispanic origin | NCHS life tables 2010–2024 (Hispanic, NH white, NH black); NHIS–LMF (`other_non_hispanic`) | NHIS–LMF `hispanic` and `black_non_hispanic`; NCHS AIAN-and-Asian composite 2019–2024; Cristia Tables 3–6 | CBO 41681 |

These fitted roles apply only while `GRADIENT_SOURCES_INCONSISTENT` has
not fired. On its trigger OACT remains primary and every competing
NCHS/NHIS source becomes a registered sensitivity, with no fitted role.
JR-C then lacks required education/race targets and stops under
`SOURCE_UNAVAILABLE`, open identification (§10); no OACT-only substitute
can satisfy Q5's three dimensions. The family keeps every member.

None of the sources reported beside is an unused holdout: this job read
them, and SM2 claims no out-of-sample check (§10, `EXPOSURE_UNRESOLVED`).

## 4. Mappings to SM1's `log_relative_risk`

SM1's coefficient is a **conditional** log relative risk against the
dimension's reference category, for one sex, single age 0–120 and path
year, added across the three dimensions and then normalized within each
age × sex × year cell (`mortality_ses/specification.py:199–254`,
`normalizer.py:328–382`). Every source publishes something else: a
**marginal** ratio between groups, or between a group and its whole
population, for a band or a single age. This section maps each published
quantity to a **marginal target** on a stated scale. Section 6 turns the
marginal targets into conditional coefficients. Each mapping below is
**[frozen here]**; each assumption carries its label into every report of
the fit.

**Common scale.** A target is `T = ln(H_g / H_ref)`, where `H_g` is
category `g`'s average annual probability of death over the target's ages,
weighted by the category's population at each single age, and `H_ref` is
the same for the reference category. Probabilities are annual `q` at the
start-of-year age that SM1 and the baseline use (`baselines/base.py:19–28`;
`mortality_ses/model.py:171–184`). This crude form matches the OACT and
NCHS education targets, which divide one category's crude rate within a
band by another's (Study 129 p. 5; NVSR 74(4) Table 14).

**NHIS targets: an age-standardized hazard ratio [frozen here].** NHIS's
estimator holds attained age fixed within each band through single-year
age terms (§4.5), so its hazard ratio is age-adjusted. A crude model-side
ratio would load any difference between two categories' age mixes onto
the category's coefficient. For an NHIS target the implied value is
therefore

`T_NHIS = ln( Σ_a W(a) μ̄_g(a) / Σ_a W(a) μ̄_ref(a) )`,

summed over the band's single ages, where `μ̄_g(a)` averages
`μ = −ln(1 − q)`, computed row by row from SM1's normalized `q`, over
category `g`'s rows at age `a` (within the target's subpopulation, rows
weighted by `w`), and `W(a)` is `R_ref(t)`'s total population of that sex
at age `a`: one fixed set of weights for both categories. Above the ACS
age top code, `W(a)` comes from §6.2's spread of top-coded records, so the
85+ band runs on single ages 85–120. The target side needs no weights:
under assumption M-H1 (§4.5) NHIS's ratio holds at every age of its band,
so any fixed standard returns it where the estimator identifies it. The
85+ targets remain unidentified under §4.5; that algebra does not supply
an age-allocation assumption. The sources read here give no reason to
prefer another standard; NHIS's own person-time would make the implied
value depend on survey records, while `R_ref(t)` is the population the
coefficients act on.

### 4.1 OACT relative mortality ratios (lifetime earnings)

- **M-E1, the target.** For sex `s`, band `B`, year `t` and quintile
  `k ∈ {q1, q2, q4, q5}`: `L_E(k) = ln RMR_k − ln RMR_q3`, from the printed
  RMRs of Tables 7–12 or the digitized RMRs of Figures 7–12. Labels map
  Lowest → `q1`, 2nd → `q2`, 3rd → `q3`, 4th → `q4`, Highest → `q5`.
  Each RMR divides a quintile's rate by the rate of all retired workers in
  that sex and band (Study 129 p. 5), so the "Total" denominator cancels
  in `L_E` and the contrast equals the log ratio of the two quintiles'
  rates. Its printing interval uses the transformed endpoints of both
  RMRs (§9.1).
- **M-E2, a rate ratio as a ratio of annual probabilities (assumption).**
  Study 129 divides deaths by exposure years, and "Deaths receive a full
  year of exposure at the age when the death occurs" (p. 5; examples in
  Appendix B, pp. 13–14). That convention makes each published rate an
  initial-exposure estimate of an annual probability of death, so this
  record reads a ratio of two quintiles' rates as a ratio of their annual
  `q`. It is still an assumption, not a source identity: the source does
  not call its rates probabilities, and its exposure counts months by age
  at last birthday.
- **M-E3, dynamic rank versus frozen rank (assumption).** OACT sorts the
  retired workers with exposure in each year by AIME within sex and
  single year of age and cuts quintiles there (pp. 3–4), so the study ranks
  survivors anew at every age; the study notes that people in high quintiles
  at younger ages move into lower quintiles at older ages (p. 3). SM3's
  attribute is a frozen partial-career rank (S0.1 §1.2). The fitted
  coefficients are contrasts between dynamic-rank groups; applying them to
  frozen-rank attributes is assumption M-E3. No source here identifies the
  difference between the two contrasts.
- **M-E4, beneficiaries versus the whole population (assumption).** OACT's
  population is retired-worker beneficiaries with a PIA, without
  WEP/totalization or older-formula records and without anyone previously
  entitled to disability benefits (pp. 3, 11); the 62–64 group consists of
  workers who claimed before their NRA and are likely less healthy than
  others that age (p. 6). Applying their contrasts to everyone, including
  people who never claimed, is assumption M-E4. In the fit, OACT targets
  apply to the reference population's Social Security recipients aged
  62–89 (§6.2), the nearest public stand-in; SM1 itself holds DI-origin
  persons at the baseline `q` (`model.py:124–160`).
- **M-E5, age basis.** OACT assigns exposure by attained age, month by
  month (p. 5); SM1 applies the year-`t` `q` at the start-of-year age. The
  mapping takes band `[a1, a2]` to SM1 ages `a1` to `a2` unchanged and
  accepts the half-year offset; sensitivity T-E4 (§5) shifts every band
  down one year.
- **M-E6, band to single ages.** One coefficient per quintile × sex ×
  band × knot, constant across the band's single ages; the reference
  population supplies the within-band composition (§6).

### 4.2 NCHS death rates by education

- **M-D1, the target.** For sex `s`, band `B ∈ {25–34, 35–44, 45–54,
  55–64}` and year `t`: `L_D(less_than_high_school) = ln q_LTHS − ln q_HS`
  and `L_D(some_college_or_more) = ln q_SC+ − ln q_HS`, where each `q`
  comes from the printed rate `m` (per 100,000, divided by 100,000) as
  `q = m / (1 + m/2)`. That conversion assumes deaths spread evenly over
  the year of age, the convention `data/life_table.py` uses for its
  closing rate (lines 21–28). The 25–64 and age-adjusted columns are not
  targets, because they repeat the band information.
- **M-D2, the pooled category.** "Some college or collegiate degree"
  pools SM's `some_college` and `college`. The model's pooled `q` over
  both categories, weighted by the reference population, matches its
  target, so NCHS identifies one combination of the two coefficients.
- **M-D3, the split.** NHIS–LMF supplies
  `ln(h_college / h_some_college)` at attained ages 25–64 by sex, pooled
  over deaths 2009–2019 and held constant over time (§4.5).
- **M-D4, ages 65 and over.** NHIS–LMF supplies marginal hazard ratios of
  `less_than_high_school`, `some_college` and `college` against
  `high_school` at attained ages 65–74, 75–84 and 85+, by sex, pooled and
  held constant over time where identified. The six required 85+ members
  remain unidentified/inconclusive under option (b), §4.5. An NHIS hazard
  `μ` maps to an annual probability
  as `q = 1 − exp(−μ)` (constant force within the year).
- **M-D5, degrees versus years (assumption).** NCHS and NHIS classify by
  highest diploma or degree; SM3's PSID attribute counts years (<12, 12,
  13–15, 16–17; S0.1 §1.2). A GED holder or a person with twelve years
  and no diploma can fall in different SM categories under the two
  definitions (S0.1 §2.3). This record maps degree-based sources by
  degree (§8.2) and reports the difference with every result.
- **Not stated.** NCHS computes category rates from stated education and
  counts "not stated" deaths only in the totals (Table 14 footnote 3), so
  the fit adjusts nothing for them and reports their share as a
  data-quality figure.

### 4.3 NCHS life tables by race and Hispanic origin

- **M-R1, the target.** For sex `s`, single age `a` from 0 to 99, and
  year `t`: `L_R(g, a) = ln q_g(a) − ln q_NHW(a)` for `g ∈ {Hispanic,
  NH black}`, from the six-decimal `qx` of the tables in §3.3.
- **M-R2, age basis.** NCHS's `qx` is the probability of dying between
  exact ages `x` and `x + 1` (NVSR 75(5) p. 2), the baseline's convention;
  the mapping is the identity.
- **M-R3, ages 100–120.** The "100 and older" interval holds no single-age
  `q`, so it supplies no contrast target (§5). The e65 targets alone read
  it, for NCHS's closing of the open interval: `e100 = T100 / l100` from
  the printed `Tx` and `lx` of that row (§9.2).
- **M-R4, `other_non_hispanic`.** NHIS–LMF supplies the marginal hazard
  ratio against `white_non_hispanic` at attained ages 25–44, 45–64,
  65–74, 75–84 and 85+, by sex, pooled and held constant over time where
  identified (fit). The two 85+ members remain unidentified/inconclusive
  under §4.5; no coarse top-code estimate supplies a fitted substitute.
  Beside it, for 2019–2024, the record reports `ln` of the ACS-weighted
  average of the AIAN and Asian NH `q` over the NH white `q`, labeled
  "partial group: no NHPI, multiracial or other people".
- **M-R5, bridged and single race (assumption).** 2010–2017 contrasts are
  bridged-race; 2018 onward are single-race; Hispanic origin does not
  change (NVSR 75(5) pp. 1–2, 54). SM's categories follow the single-race
  definitions (§8.2), and every path labels the 2017–2018 break. **A
  possible 2023–2024 change (label).** In NVSR 75(5), the 2024 tables,
  the notes under Tables 4 (p. 21), 5 (p. 23), 7 (p. 27), 8 (p. 29) and
  9 (p. 31), that is Hispanic total and male and AIAN total, male and
  female, state that NCHS applied updated classification ratios; the note
  does not appear under Table 6 (Hispanic female, p. 25), and NVSR 74(2)
  and 74(6) carry no such note. The 2024 Hispanic tables may therefore
  rest on a revised misclassification adjustment. P-PRIMARY holds the
  2024 level after the last knot (Q6, §7.1), so every path labels a
  possible 2023–2024 break for `hispanic`, and the AIAN-and-Asian
  composite beside the fit carries the same label for 2024. The fit
  reports the 2023–2024 change in the Hispanic contrasts beside the path
  and adjusts nothing for it.
- **M-R6, ratios to the total population.** For the e65 target only
  (§9.2), each group's `q` divides by the NCHS total-population `q` at the
  same age and year, and each group's open-interval `e100` divides by the
  total's.
- **Properties the source states and every report repeats:** the
  misclassification adjustment, the Medicare supplement at 66–99 for
  three groups only, modeled old-age mortality for the other groups, and
  smoothing above about 85 (§3.3).

### 4.4 Cristia's odds ratios (sensitivity and beside only)

**Log odds ratios never enter as log relative risks.** This section cites
Cristia's prose by printed page; the PDF page runs two higher (S0.1), and
the tables carry PDF pages (§3.1). Cristia's models predict death in the
next year with the bottom quintile as reference (printed p. 18). Tables 5–6 hold, for each sex and age range, a column with age
and birth year only (columns 1, 3, 5) and a column that adds race,
marital status and education (columns 2, 4, 6); the third specification
in Figure 2 (race and marital status) appears only as a plotted line.

- **M-C1, the reference population [frozen here].** For sex `s` and
  Cristia age range `b`, the reference population is the single ages in
  `b`, weighted by the stationary population `Lx` of TR 2026's
  historical period `q` for 1993 (the midpoint of Cristia's 1983–2003
  observation years; if the pinned historical file starts later, its
  earliest year, reported), with equal quintile shares. The ranges are 35–49,
  50–64 and 65–75. Tables 5–6 print the first range as "30-49", but the
  sample keeps ages 35–75 only (printed p. 8); this record reads it as 35–49 and
  reports the misprint.
- **M-C2, marginal earnings contrasts (columns 1, 3, 5).** At each age
  `a` in `b`, solve the intercept `α(a)` so that
  `0.2 × Σ_k expit(α(a) + ln OR_k) = q_base(s, a, 1993)`, with
  `OR_q1 = 1`. Then `p_k(a) = expit(α(a) + ln OR_k)`, and the band contrast
  against `q3` is `ln` of the `Lx`-weighted mean of `p_k` over that of
  `p_q3`. Quintiles map Bottom → `q1` through Top → `q5`.
- **M-C3, conditional contrasts (columns 2, 4, 6).** At a named reference
  profile (white, married, high school graduate, `q3`), solve `α(a)` so
  that the profile's probability equals `q_base(s, a, 1993)`; compute each
  category's probability at the profile with only that category changed;
  take contrasts against SM's reference categories (`q3`, `high_school`,
  `white_non_hispanic`). Cristia's education reference is less than high
  school, so the contrast against high school is the difference of two
  predicted log probabilities.
- **M-C4, category mapping (assumption).** Cristia's "White", "Black" and
  "Other Race" map to `white_non_hispanic`, `black_non_hispanic` and
  `other_non_hispanic`, and "Hispanic" to `hispanic`; Tables 3–4 list the
  four as one "Race and Ethnicity" block, and this job did not confirm
  that they are mutually exclusive.
- **M-C5, marginal group ratios (Tables 3–4).** Directly age-standardized
  one-year mortality ratios against all same-sex persons in the band
  (printed p. 14). Contrasts against a reference category are differences of
  their logs; they are rate ratios already and need no conversion.
- **M-C6, uncertainty.** Tables 5–6 print robust z statistics in
  parentheses, not standard errors (table notes), so
  `SE(ln OR) = |ln OR| / |z|`; a contrast whose printed z or odds ratio
  leaves this undefined carries no standard error. Tables 3–4 print no
  uncertainty. Marital status stays in columns 2, 4 and 6, which adjust
  for a dimension SM1 does not model.

### 4.5 The NHIS–LMF estimator

**[frozen here]** for the fit job; this job opened no NHIS record.

- **Persons.** Sample adults interviewed 2009–2018 with `ELIGSTAT = 1`,
  weighted by `SA_WGT_NEW` divided by 10 (ten pooled years).
- **Time at risk: M-H2, within-quarter timing (assumption).** Public NHIS
  supplies interview year/quarter, and the LMF supplies death year/quarter,
  not NHIS person-month follow-up (LMF dictionary p. 3). Treat every quarter
  as one quarter-year and map an interview to its quarter's midpoint.
  For a death in a later quarter, use that death quarter's midpoint. For
  a death in the interview quarter, put death halfway from the interview
  midpoint to the quarter's end: exposure is one sixteenth of a year.
  This assumes a uniform event time over the remainder of that quarter,
  conditional on survival to the midpoint. It gives every event positive
  exposure. Censor assumed survivors at the end of 2019. Sensitivity
  H-TIME replaces only same-quarter exposure by one twenty-fourth and
  one eighth of a year, the one-third and full remaining-quarter choices.
  Never drop these deaths or choose timing after seeing estimates.
  Missing/out-of-range dates, death before the interview quarter, death
  after 2019, a death date on an assumed survivor, or nonpositive event
  exposure stop the estimator under `SOURCE_UNAVAILABLE` (viii); report
  aggregate error counts only. No date repair or exclusion follows an
  outcome. Dates on linkage-ineligible persons do not enter this check.
- **Attained age.** For interview ages below 85, reconstruct birthdays
  uniformly within the year consistent with `AGE_P` at interview, split
  person-time at single-age boundaries and allocate each event's unit
  count across its possible attained ages under that same birthday rule.
  Use single-age indicators everywhere these records identify an age,
  including single ages above 84 reached during follow-up. This is a
  birthday-reconstruction assumption, not observed birthdays.
- **Open-band limit: option (b) [frozen here].** The 2018 Sample Adult
  layout p. 11 reports single ages through 84 and pools interview ages
  85 and over; the public file cannot identify their category-specific
  true-age mixes. This record freezes no age-allocation assumption for
  them. Their records do not supply an identified 85+ ratio; the six
  NHIS education 85+ members and two NHIS other-group 85+ members remain
  in §9.4's family and cannot pass. Excluding top-coded interviews would
  change the population and cannot identify the full-band target either.
  Report any estimator on that restricted population as a sensitivity
  only. `SOURCE_UNAVAILABLE` (viii), open identification, blocks the
  affected education/race dimensions and SM2's complete primary fit;
  report the supported estimates, the eight inconclusive members and
  dimension statuses. A complete diagnostic table may use §10's labeled
  sensitivities, never substitute them into P-PRIMARY. A future top-code
  allocation needs an amendment and a new registered version before use.
  This choice follows the documented lack of age information; it avoids
  claiming that proportional hazards identifies an unknown age mix.
- **Model.** For each sex, supported band and dimension, a survey-weighted
  Poisson regression of deaths on category indicators and every available
  single-year attained-age indicator, with log person-years as offset.
  Positive event exposure under M-H2 keeps that offset finite. The
  exponentiated category coefficients are marginal hazard ratios under
  the age and timing assumptions, conditional on the rank checks (§6.3).
- **M-H1, proportional hazards within a band (assumption).** Each category
  has one hazard ratio per band, constant at every single age. §4 compares
  that ratio with the model's age-standardized hazard ratio. This does
  not remove confounding from an unobserved age mix. In 85+ the desired
  estimand still spans 85–120, but the public estimator cannot identify
  it under this record; no coarse-age or elapsed-time indicator repairs
  that limit. §11.7 tests the estimator and implied value together on the
  review's unequal-age-mix example, including this inconclusive outcome.
- **Missing values.** `EDUC1` 97–99, and any race code that §8.2 leaves
  unclassified (none in the primary; `HISPAN_I` 10 and 11 under
  sensitivity X-R1), drop out of that dimension's estimate only, and the
  fit reports their counts.
- **Variance.** §9.3.

## 5. Age support and tails

SM1 needs a coefficient for every category, sex and single age 0–120 in
every path year (`specification.py:171–197`). No source covers all of
them. **A source gap never becomes an empirical zero effect**: every age
outside a source's support takes a named extrapolation, fixed below
**[frozen here]** before any fit, and each sensitivity is a registered
alternative reported beside the primary, never a replacement for it.
Extrapolations act on the fitted conditional coefficients (§6), not on
the marginal targets.

| Dimension | Ages the fit's sources support | Primary rule below | Primary rule above | Registered sensitivities |
|---|---|---|---|---|
| Lifetime earnings | 62–89 (bands 62–64 to 85–89, with backcasts before 2015 and 2020, §3.1) | `TAIL_E_HOLD_62_64_DOWN`: ages 25–61 take the 62–64 coefficient; ages 0–24 take the age-25 value | `TAIL_E_HOLD_85_89_UP`: ages 90–120 take the 85–89 coefficient | T-E1: ages 25–61 take the 65–69 coefficient instead, which avoids the early-claimer selection the source describes for 62–64 (Study 129 p. 6). T-E2: Cristia age shape (below). T-E3: a linear taper of each log contrast from its 85–89 value at age 89 to zero at age 110, and zero above, labeled "assumed convergence, not a finding" (the source reports narrower spreads at older ages, pp. 3, 8, but no rate). T-E4: every OACT band shifted one year younger (M-E5). T-B1: in place of `BAND_BACKCAST_HOLD_FIRST`, a band takes, at each knot before its first fully supported year, the targets of the next younger band fully supported at that knot: 75–79's for 80–84 and for 85–89 at 2010–2014, and 80–84's for 85–89 at 2015–2019, labeled "band backcast from a younger band" |
| Education | 25–64 (NCHS bands); 65–74 and 75–84 (NHIS–LMF); 85+ unidentified under §4.5 | `TAIL_D_HOLD_25_DOWN`: ages 0–24 take the 25–34 coefficient | The 85+ band runs to 120 | T-D1: ages 65–120 take the 55–64 coefficients, with no NHIS input, to show how much the 65+ coefficients rest on NHIS |
| Race and Hispanic origin: `hispanic`, `black_non_hispanic` | Single ages 0–99 | None needed | `TAIL_R_HOLD_99_UP`: ages 100–120 take the age-99 coefficient; the fit reads no contrast from the "100 and older" interval | T-R1: a taper from the age-99 value to zero at age 110, labeled as T-E3 |
| `other_non_hispanic` | 25–44, 45–64, 65–74, 75–84 (NHIS–LMF); 85+ unidentified under §4.5 | `TAIL_O_HOLD_25_DOWN`: ages 0–24 take the 25–44 coefficient | 85+ runs to 120 | T-R2: for 2019–2024, the partial AIAN-and-Asian composite (M-R4) replaces NHIS at every age, labeled "partial group" |

- **T-E2, Cristia's age shape.** For each sex and non-reference quintile
  `k`, let `c_b(k)` be Cristia's marginal log contrast against `q3` in age
  range `b` (M-C2). Ages 50–61 take the 62–64 coefficient times
  `c_50–64(k) / c_65–75(k)`, and ages 25–49 times
  `c_35–49(k) / c_65–75(k)`. For range `b`, the unweighted least-squares
  slope through the origin of `c_b(k)` on `c_65–75(k)` over the sex's
  four non-reference quintiles, `Σ_k c_b(k) c_65–75(k) / Σ_k c_65–75(k)²`,
  replaces a quintile's ratio when `|z| < 2` for that quintile's 65–75
  odds ratio, and every ratio stays within `[0.5, 3]`; this record
  fixes both guards to keep a ratio of small numbers from driving the
  sensitivity.
- **Ages under 25.** NCHS leaves out ages below 25 because people that
  young may not have finished their education (NVSR 74(4) p. 127); SM3's
  earnings proxy counts income from age 22 (S0.1 §1.2); and SM3's
  population starts at 50.
  The held values below 25 exist because SM1's table must be complete; a
  frame that classifies a person under 25 on either dimension must
  register that use first (§8.3). `R_ref` classifies no one under 25 on
  either dimension: it holds them at the reference categories (§6.2), so
  these held values reach no one in the fit, and SM2 models no earnings or
  education gradient below 25.
- **The baseline's top.** Ages 100–120 multiply a baseline `q` that is
  already large, and SM1 caps each probability at one and conserves the
  cell's deaths by recomputing the factor over the uncapped rows
  (`normalizer.py:338–356`). SM1 logs capped cells, and §9.1 checks the
  logs.

## 6. Joint route

### 6.1 The identification problem

The sources publish marginal contrasts: OACT's earnings ratios do not
hold education or race fixed; NCHS's education rates do not hold earnings
or race fixed; NCHS's life tables do not hold earnings or education
fixed. SM1 adds conditional log relative risks. When two dimensions vary
together within a cell, the model's implied marginal contrast for one of
them equals its own coefficient **plus** a composition term from the
other dimensions' coefficients, weighted by how the other dimensions'
categories spread across its categories. Adding marginal contrasts as
coefficients therefore reproduces the marginal targets only in a
population where the three dimensions are independent within every cell.
Correlation can make the sum overshoot or undershoot; which one depends
on the joint distribution, and no one can tell in advance (S0.1 §2.3).
Turning marginal targets into conditional coefficients needs a
**reference joint distribution** of the three attributes by sex and single
age, and an assumption that the effects add on the log scale.

### 6.2 The reference population `R_ref(t)` [frozen here]

For each knot year `t` (2010–2024), `R_ref(t)` is the weighted ACS 1-year
PUMS population of that year: every person record the file holds,
including group-quarters records where the file carries them (the fit job
records which it does), with these attributes:

- **Sex and single age.** `AGEP` gives single ages 0–99, top-coded by
  state: every record at or above its state's threshold carries the state
  mean of those ages (2024 top-coded-values document, "Explanation of
  Topcoding"; each year's thresholds and means sit in that year's
  top-and-bottom-coded-values CSV, which the fit job records; a year
  whose CSV the fit job cannot obtain counts as a missing ACS year under
  `SOURCE_UNAVAILABLE` (iii), §10). A record at
  or above its state's threshold stands for every age from the threshold
  to 120: the fit spreads its weight over those single ages in proportion
  to the stationary person-years `Lx` of the TR 2026 `q` for that sex and
  year, and each spread row keeps the record's other attributes. Below the
  threshold, `AGEP` is the single age.
- **Education and race and Hispanic origin.** From the ACS education,
  Hispanic-origin and race items through the crosswalk in §8.2; education
  at ages 25 and over only.
- **Persons under 25 [frozen here].** `R_ref` assigns no lifetime-earnings
  or education category below age 25, the record's own limit (§5, §8.3).
  Every person under 25 holds `q3` and `high_school`, the reference
  categories, whose log relative risk is zero, and the diagnostic column
  records `reference_below_25` on both dimensions (§8.1): a label, not a
  classification. Race and Hispanic origin classify at every age.
- **A lifetime-earnings quintile proxy `Q̃`.** At ages 62–89, among
  persons with positive Social Security income, `Q̃` is the weighted
  quintile of that income within sex and single age; the construction splits
  weight that straddles a quintile boundary so each quintile holds exactly
  one fifth.
  This is the public stand-in for OACT's AIME quintile (M-E3, M-E4): both
  rank people within sex and single age. OACT ranks by AIME, which orders
  people as their PIA does within a birth year (Study 129 p. 2, note 2);
  the ACS ranks by the Social Security income each person reports, which
  departs from the person's own PIA in the ways the last bullet of this
  list sets out.
- **The dependence model.** For each knot year `t` and sex `s`, on that
  year's persons with positive Social Security income aged 62–84, for
  each age group `G ∈ {62–69, 70–79, 80–84}`, a weighted ordered logit
  `P(Q̃ ≤ k | d, r, a) = expit(c_k(a) − λ_D,G[d] − λ_R,G[r])`,
  with `λ_D[high_school] = λ_R[white_non_hispanic] = 0` and cut points
  by single age, every parameter indexed by `(s, t)`. Ages 85 and over
  use `G = 80–84`, and ages 25–61 use `G = 62–69`; persons under 25 hold
  the reference categories (above). §6.6 names this copying as assumption
  M-J1.
  - **One fit per knot year [frozen here].** `R_ref(t)`, `Q̃`, the income
    amounts, the cut points and the replicate weights all belong to one
    ACS year, and §6.3 calibrates one knot at a time. A fit per year keeps
    each knot's inputs within one file, and a replicate refit then
    re-estimates exactly what the point fit estimates. `λ` enters the
    calibration as an input, not an unknown, so §6.3's system stays
    square.
  - **Weights and ties [frozen here].** The fit weights each record by
    `PWGTP` and ranks by `SSP` as the file holds it: each 1-year file
    carries a single `ADJINC` factor (data dictionaries for 2010–2019 and
    2021–2024), so a year's ranking needs no adjustment. Records with
    equal `SSP` at the same sex and single age form one block. The
    construction splits the block's cumulative-weight interval at each
    quintile boundary it spans, and every record in the block takes the
    same fractional membership of each quintile, in proportion to the
    overlap; record order inside a block changes nothing. A record enters
    the likelihood once for each quintile it belongs to, weighted by
    `PWGTP` times that fraction. Every dictionary read here marks `SSP`
    as rounded, and the 2024 top-coded-values document lists it among the
    variables top-coded at a state mean above a state threshold, so blocks
    occur.
  - **Optimizer [frozen here].** Newton–Raphson on the weighted
    log-likelihood with analytic gradient and Hessian; each age's cut
    points enter as `c_1(a)` and the logs of the gaps
    `c_k+1(a) − c_k(a)`, so they stay ordered. The start is `λ = 0`
    with cut points `logit(0.2)`, `logit(0.4)`, `logit(0.6)` and
    `logit(0.8)` at every age. Each step halves until the log-likelihood
    does not fall, at most 30 times, and the fit takes at most 100 steps.
    It has converged when every parameter moves by less than
    `1 × 10⁻⁸` and the largest gradient component, divided by the total
    weight, falls below `1 × 10⁻¹⁰`. Anything else is
    `SOURCE_UNAVAILABLE` (iv) (§10).
  - **Replicates [frozen here].** Inside each ACS replicate refit (§9.3),
    the replicate weight replaces `PWGTP` in every step above: `Q̃` and
    its blocks, the ordered logit from the same start under the same
    rules, the cut points and `P(d, r | s, a, t)`. A replicate whose
    ordered logit fails stops the procedure, as the point fit's failure
    does.
- **The joint weights.** At sex `s`, age `a` and year `t`,
  `w(k, d, r) = P(d, r | s, a, t) × P(k | d, r)`: the first factor is the
  ACS weighted share among all persons; the second comes from year `t`'s
  ordered logit for sex `s`, with cut points `c_k(s, a, t)` recomputed so
  that, at ages 62–89, every quintile holds exactly one fifth of the
  subpopulation with positive Social Security income (OACT cuts its
  quintiles at fifths of the records at each age, though their exposure
  shares can differ slightly, pp. 3–5), and at ages 25–61 and 90–120 one
  fifth of the whole population; below 25 every person holds `q3`. Each
  recomputed cut point solves its share equation by bisection until the
  share lies within `1 × 10⁻¹²` of its target. Persons without Social Security income at 62–89 take
  `P(k | d, r)` from the same model. The fit
  evaluates OACT targets on the subpopulation with positive Social
  Security income (its own `P(d, r | s, a, t)`, the same `P(k | d, r)`);
  every other target on the whole population.
- **What the proxy is not, and where it is weakest.** A benefit amount is
  not an AIME, and Study 129 itself shows how they part. The amount
  depends on when the worker claims: the NRA is the age of first
  entitlement "without an age-based reduction" (p. 6), and "workers who
  can wait to retire may do so to receive a higher monthly Social Security
  benefit" (p. 9). A person "may be entitled as a retired worker on their
  own record and as a spouse on another record", and where the spouse
  benefit is the higher, "The total benefit is the same amount as the
  full spouse benefit" (p. 8, note 1), so the total follows the other
  record, not the beneficiary's own AIME. Women
  "often became dually entitled", so that their AIME "may not have closely
  aligned with their family income level" (p. 8). The ACS item also
  counts more than a retired-worker benefit: in every year 2010–2024 its
  definition includes survivor benefits, permanent disability insurance
  payments made by the Social Security Administration, and railroad
  retirement (next bullet), none of which OACT's AIME ranking sees (M-E4);
  Study 129 does not discuss survivors. **The proxy is therefore weakest
  for women:** for a dually entitled woman, `Q̃` ranks an amount set on
  her spouse's record, not her own AIME. JR-C-W (§6.5) shows how much
  women's coefficients rest on it, and §6.6 lists what the gap leaves
  unidentified.
- **The income item's acceptance rule [frozen here].** This round read
  the item in the subject definitions for every year 2010–2024
  ("Income in the Past 12 Months", item 4; 2010 p. 79, 2024 p. 95) and in
  the data dictionaries for 2010–2019 and 2021–2024 (§13.6). The
  dictionaries define `SSP` as "Social Security income past 12 months"
  for persons 15 and over. The subject definitions hold two wordings, one
  for 2010–2016 ("Social Security income includes Social Security
  pensions and survivor benefits, permanent disability insurance payments
  made by the Social Security Administration prior to deductions for
  medical insurance, and railroad retirement insurance checks from the
  U.S. government. Medicare reimbursements are not included.") and one for
  2017–2024, headed "Social Security or Railroad Retirement income", which
  reads "Social Security and U.S. railroad retirement pensions and
  survivor benefits" in place of "Social Security pensions and survivor
  benefits" and is otherwise the same. Both describe the same benefit
  types, which this record takes as the proxy's stated content, not as a
  failure. For each year it uses, the fit job checks the year's subject
  definition and `SSP` dictionary entry: a file whose SHA-256 equals the
  one §13.6 lists passes, and any other copy passes when the item's text
  matches the frozen wording for its years, line breaks and spacing aside.
  A year that fails, or whose documents the fit job cannot obtain (any future replacement included), takes `λ` from the nearest passing year, the
  earlier year on a tie, keeps its own file for everything else, and
  carries the label "income-item definition borrowed from" that year. If
  no year passes, `SOURCE_UNAVAILABLE` (vi) applies (§10).

### 6.3 Joint marginal calibration [frozen here]

Before this route runs, apply §10's disagreement consequence. If it
removes competing sources, JR-C stops; no remaining source supplies its
required education/race targets. Otherwise, for each knot `t` and sex `s`,
the unknowns are:

| Block | Unknowns | Targets |
|---|---|---|
| Lifetime earnings | 4 non-reference quintiles × 6 bands = 24 | 24 OACT contrasts (M-E1), including backcast copies (§3.1) |
| Education, 25–64 | `less_than_high_school` and `some_college` per NCHS band (8), plus one split `δ_s`, with `college = some_college + δ_s` in every band | 4 bands × 2 NCHS contrasts (M-D1, M-D2) plus the NHIS split (M-D3) = 9 |
| Education, 65+ | 3 non-reference categories × 3 bands = 9 | 9 NHIS contrasts (M-D4) |
| `hispanic`, `black_non_hispanic` | 2 × 100 single ages = 200 | 200 NCHS contrasts (M-R1) |
| `other_non_hispanic` | 5 bands | 5 NHIS contrasts (M-R4) |

That is 247 equations in 247 unknowns per knot and sex. Coefficients at
ages outside these blocks follow §5. Below 25, `R_ref` holds everyone at
`q3` and `high_school` (§6.2), so its rows there vary by race and
Hispanic origin only, and the race coefficients at ages 0–24 carry no
earnings or education composition. At ages 25–61 they and the education
coefficients come out net of an earnings composition that rests on the
copied dependence (M-J1, §6.6). The fit computes each target's implied
value by expanding `R_ref(t)` into
rows, one per (quintile, education,
race) combination at each single age, with weight `w`, applying the
candidate coefficients and SM1's `normalize_probabilities` cell by cell
against the baseline `q`, and averaging the normalized probabilities over
the target's ages and subpopulation: crude for OACT and NCHS targets, and
age-standardized hazards for NHIS targets (§4, common scale).

- **Solver.** Newton's method on the full system, started from the
  plain-addition coefficients (JR-A); convergence when every implied
  target is within `1 × 10⁻¹⁰` of its target in log units. Each step
  starts from the full Newton step and halves it, up to 30 times, until
  the sum of squared log residuals falls; a start that would need a 31st
  halving, or that has not converged after 100 steps, fails to converge.
  A second start from all-zero coefficients must reach the same solution
  within `1 × 10⁻⁹`. Agreement checks numerical reproducibility at two
  prescribed starts; it proves neither identification nor global uniqueness.
- **Support and rank before conformance residual inspection.** At each
  knot, sex and replicate, first require positive reference weight in
  every target category and its reference, at every single age and
  subpopulation entering that target. Form the weighted model design
  matrix `X`: one row per positive-weight expanded cell, columns for
  precisely the 247 free coefficients above, with the split and tail
  equalities substituted and reference columns removed. Multiply each row
  by its square-root weight; normalize each nonzero column to unit norm.
  Require full column rank by SVD: every singular value must exceed
  `1 × 10⁻¹⁰` times the largest. A zero column fails support.
  Also check the analytic Jacobian `J = ∂(implied target vector)/∂β`
  of §6.3's 247 log contrasts, including normalization and all weight
  averages. Normalize its nonzero columns the same way and require the
  same SVD rank at both starts, every accepted Newton iterate and each
  final solution, before inspecting residuals for conformance. At a
  clipping boundary require the check for both one-sided Jacobians;
  inability to evaluate either leaves identification unresolved.
  Run the corresponding category/single-age design check on each NHIS
  Poisson fit and the free-parameter design on each ordered logit too.
  Missing support, deficient rank or an unavailable derivative stops
  that knot/replicate under existing `SOURCE_UNAVAILABLE` (viii), open
  identification, and blocks its dimension and SM2. Never inspect a
  favorable residual and then repair rank by dropping a column, imposing
  a penalty or changing a target. These checks tighten S2-14's proposal;
  full local rank does not prove global uniqueness.
- **Failure.** If either start fails to converge, or the two disagree,
  the knot's calibration fails. That is a gate failure, not a tuning
  opportunity (§10, `GATE_FAIL_OR_REGRESSION_FAIL`), and whether it
  happens is an outcome this record does not predict (row S2-17).

### 6.4 Candidate routes

| Route | What it identifies | Reference distribution it needs | Where it comes from without PSID | What the public NHIS–LMF can and cannot supply | How it can go wrong |
|---|---|---|---|---|---|
| **JR-A: plain addition of marginals** | Each dimension's marginal contrast in its own source population; nothing joint | None; it assumes the three attributes are independent within every cell | Not needed | Not needed. It could check the education × race association, which this route ignores | Double counting wherever the dimensions vary together in the same direction of risk, and the reverse where they vary in opposite directions; the size depends on the deployment population and goes unmeasured |
| **JR-B: education × race joint, earnings independent** | Education and race coefficients adjusted for each other; the earnings coefficient equals OACT's marginal contrast | `P(d, r \| s, a)` | ACS PUMS (§6.2), with `λ = 0` | Can supply the education × race association in its own population as a check; cannot supply anything about earnings | Counts the earnings–education and earnings–race overlap twice |
| **JR-C: full joint calibration with a public earnings proxy (primary)** | Conditional coefficients that reproduce every marginal target on one named population, given the proxy's dependence and log-additivity | `P(k, d, r \| s, a)` | ACS PUMS with the Social Security income quintile and the ordered logit (§6.2) | Supplies the education targets at 65+, the split and `other_non_hispanic`; cannot supply the earnings dependence | The proxy's dependence differs from the AIME quintile's (§6.6); effects interact rather than add; the dependence in the deployment population (PSID cohorts) differs from the ACS's |
| **JR-D: Cristia-bridged shrinkage** | The 1983–2003 ratio of mutually adjusted to marginal contrasts in SIPP–SSA data at 35–75, carried to modern marginals | None named; it is implicit in Cristia's sample | Cristia's Tables 3–6 | Nothing | The ratio may not carry across two to four decades and a different population; columns 2, 4, 6 also adjust for marital status; rounded z statistics; it reproduces no modern marginal on any named population, so no e65 check applies |
| **JR-E: NHIS direct joint model** | Education and race hazard ratios adjusted for each other in NHIS's 2009–2019 population; earnings as JR-B | The NHIS sample itself | NHIS–LMF | Supplies everything for education × race at attained ages 25+; cannot supply earnings, single ages above 84 at interview, or deaths after 2019 | Does not reproduce NCHS's targets (different population, years and reporting); survey precision; the earnings overlap as JR-B |
| **JR-F: PSID reference population (not used, §12)** | As JR-C, with the deployment population's own joint distribution | The PSID cohort's lifetime-earnings × education × race distribution | — | — | PSID use follows the project's data-access record. This record does not use it; §12 states the rule for the primary |

**JR-D's definition [frozen here].** For dimension `X`, sex `s` and
Cristia age range `b`, `κ_X(s, b)` is the weighted least-squares slope,
through the origin, of Cristia's conditional log contrasts (M-C3) on its
marginal log contrasts (M-C2 for earnings, M-C5 for education and race),
across the dimension's non-reference categories, with weights equal to
the categories' shares in Cristia's sample: for race and ethnicity, Table
1's "Weighted" column (PDF p. 36), which pools sexes and ages; for
education, the mean of Table 2's two Mortality Sample columns, 1984 and
1996 (PDF p. 37); for earnings quintiles, equal weights, since each
quintile holds a fifth by definition. The same weights serve every sex
and age range, because neither table splits by them. `κ` stays within
`[0, 1]`. JR-D's coefficients
are `κ` times JR-A's, and ages outside 35–75 take the nearest range's `κ`.

### 6.5 Choice

**Primary: JR-C, subject to §10's disagreement and identification stops.**
A disagreement promotes competing sources to sensitivities and leaves no
admissible complete joint route. Sensitivities: JR-A (labeled "plain addition of
marginals"), JR-B (JR-C with `λ = 0`), JR-C with `λ` scaled by 0.5 and by
1.5, JR-C-IND and JR-C-W (below), JR-D and JR-E. Reasons:

1. **Q5 asks for one model.** "Education and race and Hispanic origin are
   further dimensions of the same model" calls for coefficients that hold
   the other dimensions fixed. JR-A and JR-B set some of that adjustment
   to zero by construction, and JR-D borrows it from another era.
2. **It makes S0.1's e65 conformance computable.** S0.1 requires a fixed
   reference population and marginalization for the e65 target (§2.5).
   Only routes that calibrate on a named population can reproduce a
   marginal target there; JR-C reproduces all of them on one population.
3. **Its inputs are public and current.** The ACS covers every knot year
   and is the same survey NCHS uses for its education denominators
   (NVSR 74(4) p. 132).
4. **It measures what the others assume.** JR-A and JR-B fix the
   earnings–education/race dependence at zero; JR-C estimates it with a
   stated proxy, and the `λ` sensitivities and JR-D bracket it.
5. **Q5's primacy of earnings stays visible.** Every route keeps OACT's
   contrasts as the earnings targets; no route lets an education or race
   source move them.

**JR-C-IND, independence wherever the fit copies the dependence [frozen here].**
Wherever M-J1 copies the dependence (§6.6), JR-C-IND sets
`P(k | d, r) = 1/5` for every education and race category, and keeps the
estimated dependence for recipients aged 62–84 only. Its label is
"dependence outside recipients aged 62–84 set to independence". It shows
how much the coefficients at ages 25–61 and 85 and over, and the targets
evaluated on the whole population, rest on the copy.

**JR-C-W, women's dependence from men's [frozen here].** The proxy is
weakest for women (§6.2). In JR-C-W, women's ordered logit takes men's
`λ_D,G` and `λ_R,G` of the same knot year and age group, and women's cut
points follow §6.2's recomputation; men's tables equal JR-C's. Its label
is "women's dependence borrowed from men". The calibration runs
separately for each sex (§6.3), so JR-B's women's tables already show
`λ = 0` for women alone, and JR-C-W adds the other alternative: the
dependence men show.

### 6.6 What stays unidentified

- **The dependence between OACT's AIME quintile and education or race.**
  The Social Security income quintile stands in for it. Benefits that do
  not follow the person's own AIME move the proxy away from OACT's
  quintile: claiming-age reductions (Study 129 pp. 6, 9), the full spouse
  benefit that a dually entitled beneficiary receives in total (p. 8,
  note 1), and the survivor, disability and railroad retirement benefits
  that the ACS item counts and OACT's AIME ranking never sees (§6.2,
  M-E4). **The gap is widest for women**, whose AIME the study says "may
  not have closely aligned with their family income level" (p. 8): for a
  dually entitled woman, the proxy ranks an amount set on the spouse's
  record. No public source settles which way these move the estimated
  dependence; JR-C-W (§6.5) shows how much women's coefficients rest on
  it.
- **M-J1, the copied dependence (assumption).** The ordered logit sees
  only recipients aged 62–84 (§6.2). The fit applies that dependence to
  persons it never observed: non-recipients at 62–89, everyone at 25–61,
  recipients at 85–89 (through `G = 80–84`) and everyone at 90–120. No
  public source shows how lifetime earnings depend on education and race
  in those groups. The copy shapes other coefficients: at ages 25–61 the
  education and race coefficients come out net of an earnings composition
  nobody observes (§6.3), and the targets evaluated on the whole
  population carry it. JR-C-IND (§6.5) replaces the copy with
  independence. Below 25 the fit copies nothing: `R_ref` holds everyone at the
  reference categories, so SM2 models no earnings or education gradient
  there, and the race coefficients at 0–24 carry no earnings or
  education composition.
- **Interactions.** The model assumes the three effects add on the log
  scale. No public source has all three jointly with modern deaths. The
  fit job reports NHIS's education × race interaction terms at 65+ as a
  diagnostic; it does not gate on them.
- **The dynamic-versus-frozen rank difference** (M-E3), and the
  degree-versus-years education difference (M-D5).
- **The earnings gradient below 62 and above 89, and every tail in §5.**
- **The time paths of the NHIS-based coefficients.** NHIS's pooled
  2009–2019 contrasts hold constant across the knots.
- **DI origin.** The fit treats every reference-population member as
  free; SM1 holds DI-origin persons at baseline in deployment, and S0.1
  frozen text notes that this agrees with OACT's exclusion "in direction"
  without proving equal definitions (S0.1 §2.3).

## 7. Paths over time

### 7.1 Primary path P-PRIMARY (Q6) [frozen here]

- **Knots.** Every calendar year 2010–2024, the same fifteen years for all
  three dimensions. At each knot `t`, each dimension's targets are its
  latest observed values at or before `t`; before a dimension's first
  observation it takes that first observation (hold-first backcast); the
  three then calibrate jointly on `R_ref(t)` (§6.3). The result is one
  complete coefficient table per knot (§7.5).
- **After the last knot.** SM1's `HoldLastCoefficientPath` holds the 2024
  table for every later year and refuses years before 2010
  (`specification.py:76–106`). That holding is Q6's primary path: the
  gradient stays at its last observed level.
- **Last observed year per dimension.** Lifetime earnings 2022 (Study 129
  Figures 7–12; the last table year is 2020); education 2022 (NVSR 74(4));
  race and Hispanic origin 2024 (NVSR 75(5)); the NHIS-based targets pool
  deaths 2009–2019 and stay the same at every knot.

| Knot | Lifetime earnings targets | Education targets, 25–64 | Race and Hispanic origin targets |
|---|---|---|---|
| 2010 | Table 10 (2010); 80–84 from 2015 and 85–89 from 2020 by backcast | 2018 national, by backcast (`EDU_BACKCAST_HOLD_FIRST`) | NVSR 63(7), bridged race |
| 2011–2014 | Figures 7–12; 80–84 and 85–89 by backcast | 2018 by backcast | NVSR 64(11), 65(8), 66(3), 66(4), bridged |
| 2015 | Table 11 (2015); 85–89 by backcast | 2018 by backcast | NVSR 67(7), bridged |
| 2016–2017 | Figures 7–12; 85–89 by backcast | 2018 by backcast | NVSR 68(4), 68(7), bridged |
| 2018 | Figures 7–12; 85–89 by backcast | NVSR 69(13) I–7 | NVSR 69(12), single race |
| 2019 | Figures 7–12; 85–89 by backcast | NVSR 70(8) I–7 | NVSR 70(19) |
| 2020 | Table 12 (2020) | NVSR 72(10) I–7 | NVSR 71(1) |
| 2021 | Figures 7–12 | NVSR 73(8) Table 14 | NVSR 72(12) |
| 2022 | Figures 7–12 | NVSR 74(4) Table 14 | NVSR 74(2) |
| 2023 | Held at 2022 | Held at 2022 | NVSR 74(6) |
| 2024 | Held at 2022 | Held at 2022 | NVSR 75(5) |

Every knot also lists the NHIS-based targets (education at 65+, the
split, `other_non_hispanic`), including the eight unidentified 85+ members
that prevent a complete admitted primary fit under §4.5. "Held" means the fit imposes the same
published targets again on that year's reference population, so the
conditional coefficients can still move with the population's
composition.

### 7.2 Extracting and digitizing the earnings gradient [frozen here]

- **Tables.** Two independent text-layer readers (Poppler's
  `pdftotext -layout` and a second PDF library) each transcribe Tables
  1–12 of Study 129 and Tables 4–8 of Study 124; the two transcriptions
  must agree on every printed string, or the job stops and reports the
  cells.
- **Figures 7–12 (pp. 33–38).** The series are vector paths (§3.1). The
  digitizer decompresses each page's content stream, reads the axis tick
  labels and their positions from the text layer, fits a linear map from
  page coordinates to RMR on the y-axis and to year on the x-axis (at least
  three ticks per axis per panel; a tick fit whose worst residual exceeds
  0.1 percent of the axis range rejects the panel), assigns each polyline
  to a legend entry by stroke color and dash pattern, and reads the vertex
  nearest each integer year (within a quarter year). Each point keeps its
  page, panel, series and page coordinates.
- **Validation.** At every table year in which a table prints the band, the
  digitized RMR must lie within 0.010 of the printed two-decimal value
  (the printed value's 0.005 rounding plus a plotting tolerance of
  0.005). There are 210 such points: 21 band-years × 2 sexes × 5
  quintiles. Every one must pass; if any fails, the figure years are
  unavailable (§10, `SOURCE_UNAVAILABLE`), and nobody can build P-PRIMARY.
- **Digitization half-width.** `δ_dig` is the largest
  `|digitized − printed|` over the 210 validation points, plus 0.005.
  Each digitized value then stands for the interval `±δ_dig` around it,
  which §9 treats like a printing interval.
- **Which values the fit uses.** Printed table values at 2010, 2015 and
  2020; digitized values at 2011–2014, 2016–2019 and 2021–2022; only for
  fully supported bands (§3.1).
- **Coverage.** With the backcasts, every knot has all six earnings
  bands, both sexes and all four non-reference quintiles; §5 completes
  ages 0–61 and 90–120.

### 7.3 Registered sensitivities over time [frozen here]

- **P-TABLE (table only).** Earnings targets from Tables 7–12 alone:
  2010 for knots 2010–2014, 2015 for 2015–2019, and 2020 for 2020–2024;
  the other dimensions as in P-PRIMARY. Its last earnings level is 2020,
  so it cannot become the primary path without amending Q6 (S0.1 §2.3).
- **P-PRE (pre-pandemic).** From the 2020 knot onward, every dimension's
  targets hold at their 2019 values. Reason: Study 129 reports that the
  pandemic changed some groups' spreads in 2020 and 2021 and that the
  changes "seem to be temporary" (p. 9), while Q6's last observed year
  for earnings, 2022, falls in that period.
- **E-S1 (reporting-state education).** Education targets at knots
  2010–2017 from that year's reporting-state tables (§3.2) instead of the
  2018 backcast, labeled "not national".

### 7.4 The widening alternative P-WIDEN (Q6) [frozen here]

A custom `CoefficientPath` (`specification.py:62–73`) that equals
P-PRIMARY at every knot through 2024 and, for `t > 2024`, multiplies every
non-reference **lifetime-earnings** and **education** coefficient, at every
age and for both sexes, by

`m(t) = min(1 + g × min(t − 2024, 30), 1.5)`, with `g ≥ 0`.

| Element | Value | Source or reason |
|---|---|---|
| Origin | 2024 | P-PRIMARY's last knot, so the alternative departs only where no data exist |
| Earnings slope `g_E(s, B)` | For each sex and OACT band with at least ten annual points in 2005–2019: the least-squares slope, over those years, of `S(t) / S̄`, where `S(t) = L_E(q1)(t) − L_E(q5)(t)` from the annual figures and `S̄` is its mean over the same years. Bands with fewer points (80–84, five points; 85–89, none) take the mean of the 70–74 and 75–79 slopes for the same sex, each computed as above before the zero floor; the floor below then applies to the mean. Ages outside 62–89 take the nearest band's slope | Study 129 calls the gradient's trends "generally, slowly growing" (p. 10); 2005–2019 are the fifteen pre-pandemic years with at least three bands present, and the estimator leaves out the pandemic years because of p. 9 |
| Negative slopes | Set to zero: no widening for that sex and band, which then equals P-PRIMARY | The alternative is a widening path; a fitted narrowing is not evidence for it |
| Education slope `g_D(s)` | `g_E(s, 62–64)` | No national education series longer than five years exists (§3.2); 62–64 is the earnings band nearest NCHS's ages |
| Race and Hispanic origin | `m(t) = 1`, held flat | CBO 41681 says the gaps between whites and blacks "have narrowed somewhat" (p. 2), with a qualifier on p. 1: the black–white gap held for men and narrowed for women; no source here supports a widening race path |
| Ages | Every age 0–120 (the tails follow §5's rules applied to the multiplied coefficients) | One rule for the whole table |
| Caps | The multiplier stops growing after 30 years (2054) and never exceeds 1.5 | The source series spans 1995–2022, about 30 years; the alternative carries no trend further than the data it comes from |

The path's `years` are P-PRIMARY's knots plus 2025–2054; every later year
returns the 2054 table. SM1 revalidates each returned table and still
normalizes every cell (Q4), so widening moves deaths between groups and
never adds deaths. The fit job computes the slopes under this
frozen estimator; this record computes none.

### 7.5 Synchronization

Source unavailability never changes the frozen last-observed years
(earnings 2022, education 2022, race 2024). Section 10 governs missing
files before this rule runs: an earlier-year sensitivity cannot become
Q6's primary, and no unavailable member leaves the family.
One rule covers every path: all three dimensions share the same knot
years; at each knot each dimension takes its latest observed targets at
or before the knot (hold-first before its first observation); the joint
calibration then yields one complete table holding every dimension ×
category × sex × single age 0–120, which `RelativeRiskSpec` validates
(`specification.py:171–197`). No dimension carries its own knot years
into SM1. **Q11:** SM owns death alignment, so these coefficients assume
the TR 2026 baseline `q` and nothing downstream aligns deaths a second
time (design §7.2).

## 8. Schema

### 8.1 Dimensions [frozen here]

This record confirms S0.1's proposed table against
`mortality_ses/specification.py` (`RiskDimension`, lines 34–59;
`RelativeRiskSpec`, lines 145–197) and tightens it in one respect: each
dimension has one unclassified string, and
the reason a person lacks a category goes in a separate diagnostic column
`sm_<dimension>_unclassified_reason`, never into the dimension column. SM1
also treats a missing value as unclassified (`specification.py:224–227`).
The same column carries `reference_below_25` for a person under 25 in
`R_ref`, who holds `q3` and `high_school` by rule rather than by
classification (§6.2). SM1 reads only the dimension and `sex` columns
(`specification.py:203–224`), so the label changes no risk.

| `name` | `column` | `categories`, in this order | `reference` | `unclassified_values` |
|---|---|---|---|---|
| `lifetime_earnings` | `sm_lifetime_earnings_quintile` | `q1`, `q2`, `q3`, `q4`, `q5` (lowest to highest) | `q3` | `("unclassified",)` |
| `education` | `sm_education` | `less_than_high_school`, `high_school`, `some_college`, `college` | `high_school` | `("unclassified",)` |
| `race_hispanic_origin` | `sm_race_hispanic_origin` | `hispanic`, `white_non_hispanic`, `black_non_hispanic`, `other_non_hispanic` | `white_non_hispanic` | `("unclassified",)` |

### 8.2 Crosswalks [frozen here]

**Education.**

| SM category | Meaning | NCHS death certificate | NHIS `EDUC1` | ACS | SM3's PSID years (S0.1 §1.2) |
|---|---|---|---|---|---|
| `less_than_high_school` | No high school diploma or GED | "Less than high school diploma or GED" | 00–12 | `SCHL` 01–15 (no schooling through "12th grade - no diploma") | Fewer than 12 |
| `high_school` | Diploma or GED, no college | "High school diploma or GED" | 13–14 | `SCHL` 16–17 ("Regular high school diploma", "GED or alternative credential") | 12 |
| `some_college` | Some college without a degree, or an associate degree | Within "Some college or collegiate degree" | 15–17 | `SCHL` 18–20 (some college, no degree; associate's degree) | 13–15 |
| `college` | Bachelor's degree or higher | Within "Some college or collegiate degree" | 18–21 | `SCHL` 21–24 (bachelor's, master's, professional, doctorate) | 16–17 (the reader's upper code) |
| `unclassified` | — | "Not stated" | 96–99 | None at 25 and over: `SCHL` covers every person aged 3 and over ("bb" marks under 3), and §6.2 holds everyone under 25 at `high_school` | Missing |

The ACS codes come from the data dictionaries for 2010–2024 (§13.6,
§13.7). Fix round 2 compared the 2020 experimental dictionary's `SCHL`,
`HISP` and `RAC1P` codes and labels with this crosswalk: they match.
`SCHL` retains its 24 codes and under-3 blank code; `HISP` retains 01–24
and `RAC1P` 1–9. The 2010 and 2011 `RAC1P` 9 wording differs as §13.6
records, with the same mapping. **The 2020 code-list item closes.**
The 2020 variable-changes document pp. 2–4 names none of these three
variables among changed codes; it explicitly keeps the weight names
while using experimental person and replicate weights. The fit must use
those 2020 experimental weights. This code/label check computes no ACS
quantity and does not certify data URLs or survey precision. The fit
job still checks `AGEP` and `SSP` against §6.2; this code-list closure
waives neither check nor its existing failure rule. For every year the loader tests that each code lands in exactly one category. NHIS codes come from the 2009, 2016 and 2018 person layouts (pp. 265, 296,
294).

**Race and Hispanic origin.**

| SM category | NCHS life tables | NHIS (`HISPAN_I`, `RACERPI2`) | ACS | Cristia |
|---|---|---|---|---|
| `hispanic` | Hispanic (any race) | `HISPAN_I` 00–11 | `HISP` 02–24 | Hispanic |
| `white_non_hispanic` | NH white (single race from 2018; bridged 2010–2017) | `HISPAN_I` 12 and `RACERPI2` 01 | `HISP` 01 and `RAC1P` 1 ("White alone") | White |
| `black_non_hispanic` | NH black | `HISPAN_I` 12 and `RACERPI2` 02 | `HISP` 01 and `RAC1P` 2 ("Black or African American alone") | Black |
| `other_non_hispanic` | No complete table; AIAN NH and Asian NH (2019–2024) form a partial group | `HISPAN_I` 12 and `RACERPI2` 03–06 (AIAN only, Asian only, not releasable, multiple race) | `HISP` 01 and `RAC1P` 3–9 (American Indian, Alaska Native and other AIAN codes, Asian, NHPI, some other race alone, two or more races) | Other Race |
| `unclassified` | — | None in the primary; `HISPAN_I` 10 and 11 under sensitivity X-R1 | None: `HISP` and `RAC1P` code every person | — |

`HISPAN_I` 00–11 map to `hispanic` and 12 to the non-Hispanic groups, as
S0.1 froze it ("00–11 Hispanic, 12 non-Hispanic", audit lines 468–469,
inside the **[frozen findings]** block that opens at line 453).
The 2018 layout's note puts respondents who "refused to answer Hispanic
origin" in 10 and those who "didn't know it" in 11, and adds "When
Hispanic origin was not ascertained, this variable was also assigned
"11"" (2018 Sample Adult layout, p. 8). Codes 10 and 11 therefore get the
same treatment in every run: `hispanic` in the primary, and `unclassified`
in sensitivity X-R1, which drops both from the race estimates (§4.5). The
same note places under 12 respondents who "answered 2,7,8, or 9 in
ORIGIN_I", a variable this record does not read. The public files carry
no flag showing whether NCHS imputed race or ethnicity (2018 survey
description pp. 25–26), so the fit cannot set imputed values apart.

**Lifetime earnings.** OACT's Lowest through Highest, Cristia's Bottom
through Top, the ACS proxy `Q̃` and SM3's PSID quintiles all map to `q1`
through `q5`. SM3's quintile is `unclassified` when a person has fewer than
ten observed head or spouse years (S0.1 §1.2).

**How these differ from `estimates/group_breakdown.py`.** That module's
MINT education dimension (lines 1227–1274) has five bands by years of
education: `graduate` (more than 16), `bachelor` (16), `associate`
(14–15), `high_school` (12–13) and `less_than_high_school` (less than 12).
Its race dimension (lines 1103–1130) uses `hispanic_any_race`,
`white_non_hispanic`, `black_non_hispanic` and `other_non_hispanic`. SM's
four education categories are a new crosswalk: SM's `high_school` is 12
years where MINT's is 12–13, and SM's `some_college` (13–15) and `college`
(16–17) cut where MINT's bands do not. SM's `hispanic` is the same concept
as MINT's `hispanic_any_race` under a different string. SM's columns carry
the `sm_` prefix, SM never reuses MINT's dimension objects, and the fit
job's tests assert that the two schemes stay separate, so the out-of-scope
group definitions do not change.

### 8.3 `unclassified_rule` by use [frozen here]

| Use | Rule | Reason |
|---|---|---|
| SM2's fit and conformance on `R_ref` | `refuse`, applied after §6.2's under-25 rule and §8.2's crosswalk | Those rules leave no reference-population person unclassified: everyone aged 25 and over carries a `SCHL` code 01–24, everyone carries `HISP` and `RAC1P` codes, everyone under 25 holds the reference on earnings and education, and everyone else at 25 and over takes `Q̃`'s quintile weights (§6.2). A person who still appears unclassified is a construction error, which stops the run and goes into the fit's report |
| SM2's NHIS estimates | Not through SM1 | §4.5 drops unclassified persons from that dimension's estimate and reports the count |
| SM3 | `reference` (confirms S0.1 §2.3) | SM3's estimand keeps unclassified persons in the overall ratio and in no group cell (S0.1 §1.1); under `reference` they take zero log risk on that dimension, SM1 still conserves the cell, and the cell log counts them (`specification.py:219–247`; `normalizer.py:17–35`) |
| Any projection (Track B, the open population) | `refuse` until the frame carries all three attributes and a registration names the rule | `FRAME_ATTRIBUTE_MISSING` (§10) |

A person under 25 classified on lifetime earnings or education needs a
registration of its own before any use (§5). `R_ref` classifies no one
under 25 on either dimension: it holds them at the reference categories by
rule, labeled `reference_below_25` (§6.2, §8.1), and that rule is not such
a classification.

## 9. Conformance procedure: `SM2_SOURCE_RECONSTRUCTION_AND_CLUSTER_BOOTSTRAP`

**[frozen here]** throughout, unless a step names S0.1. The procedure runs
on P-PRIMARY under JR-C where the identification/source checks allow it.
Run those checks before conformance residual inspection; retain every
unavailable member and publish supported steps and all statuses (§4.5,
§6.3, §9.5, §10). Sensitivities run the same steps and report;
they do not gate. Its order:

1. Pin every input: source files at the hashes in §13 and the fit job's
   manifest, module versions, the seed (§9.3), and the reference
   population files.
2. Build P-PRIMARY's fifteen tables (§7.1) and validate each with
   `RelativeRiskSpec`.
3. Run the deterministic reconstruction checks (§9.1).
4. Compute the e65 residuals (§9.2) and every family member's
   simultaneous bound (§9.3, §9.4).
5. Run the invariants (§9.6).
6. Apply the pass conjunction (§9.5).

### 9.1 Deterministic reconstruction checks (tier A)

These run at the point estimate and carry no Monte Carlo error. Any
failure stops the procedure (§10, `GATE_FAIL_OR_REGRESSION_FAIL`).

- **A1, exact printing intervals.** For a target built from two printed
  values `r_k` and `r_ref` with half-width `h`, the interval for
  `L = ln r_k − ln r_ref` uses the transformed endpoints of both:
  `[ln(r_k − h) − ln(r_ref + h), ln(r_k + h) − ln(r_ref − h)]`. The
  procedure never uses the approximation `h / r` as a log tolerance (S0.1
  §2.5). The half-widths are 0.005 for an RMR; 0.0000005 for a six-decimal `qx`;
  0.5 for a printed `lx` or `Tx` (used only in §9.2's open interval);
  0.05 per 100,000 for an NCHS education rate, carried through
  `q = m / (1 + m/2)`; `δ_dig` (§7.2) for a digitized RMR; and zero for an
  NHIS estimate this project computes. The model-implied contrast must lie
  inside the interval widened by **ε = 1 × 10⁻⁶** in log units on each
  side. ε is the only extra residual tolerance this record sets: it covers
  the solver's `1 × 10⁻¹⁰` convergence and floating-point accumulation,
  and it cannot relax e65's limit. Where `r − h ≤ 0` leaves an endpoint
  undefined, that side of the interval has no bound and the check applies
  to the other side only.
- **A2, the source agrees with itself.** For every quintile, band, sex and
  table year, the interval for `ln(rate_k / rate_q3)` from Tables 1–6
  (four-decimal rates) must overlap the interval for `L_E(k)` from Tables
  7–12. A failure means a transcription error, not a source finding.
- **A3, digitization.** All 210 validation points pass (§7.2).
- **A4, two transcriptions agree** on every printed string (§7.2).
- **A5, SM1's cell log on `R_ref`.** At every knot, no cell is
  infeasible, every feasible cell conserves its deaths, and the fit reports
  the counts of capped rows (`normalizer.py:17–35`).
- **A6, coverage.** Every knot's table holds every dimension × category ×
  sex × age 0–120 once, with zero reference coefficients
  (`specification.py:171–197`).

### 9.2 Life expectancy at 65 [frozen here; limit frozen, S0.1 §2.5]

- **Reference population and marginalization.** For group `g` of a
  dimension, sex `s`, knot `t` and single age `a`: `h_g(a)` is the
  average of SM1's normalized probabilities over `g`'s rows of `R_ref(t)`
  (the other two dimensions' categories weighted by `w`), within the
  target's subpopulation: Social Security recipients at 62–89 for OACT
  targets and the whole population otherwise, and the whole population at
  every age above the subpopulation's range. `h_all(a)` is the same
  average over every row of that subpopulation. The fitted group
  probability is `q_F,g(a) = q_base(s, a, t) × h_g(a) / h_all(a)`.
- **Earnings targets.** `q_T,g(a) = min(1, q_base(s, a, t) × ρ_g(a))` at
  every age 0–120, with `ρ_g` the RMR of `g`'s band at the knot (after
  backcasts and holds; above 89 the 85–89 RMR), and
  `e65_T,g = life_expectancy(q_T,g[0..120], 65)` under the closing rule
  below. OACT publishes RMRs, not life tables, so it has no closing of its
  own, and S0.1 asks for a fixed tail rule (audit lines 643–646).
- **Race and Hispanic-origin targets keep NCHS's conventions.** S0.1
  requires "the source's age/closing conventions" for NCHS life-table
  targets (audit lines 647–648). At single ages 65–99,
  `q_T,g(a) = min(1, q_base(s, a, t) × ρ_g(a))`, with
  `ρ_g(a) = q_g(a) / q_total(a)` from the knot's NCHS tables for
  `hispanic`, `white_non_hispanic` and `black_non_hispanic` (M-R6), and
  `q_source,other(a) = 1 − (1 − q_NHW(a))^HR_b(a)` followed by
  `ρ_other(a) = q_source,other(a) / q_total(a)` for `other_non_hispanic`.
  Only then rescale by `q_base` and cap, as above. `HR_b(a)` is the NHIS
  hazard ratio of `a`'s band. M-D4's constant-force conversion acts on the
  source NH white probability before its ratio to the source total;
  applying HR to either a probability or the already rescaled baseline
  would define a different target. The 85+ input remains unidentified
  under §4.5, so this formula specifies a target, not an available value. Survivors run
  `l(65) = 1` and `l(a + 1) = l(a)(1 − q_T,g(a))`, and person-years
  `L(a) = (l(a) + l(a + 1)) / 2`, NCHS's equation 17 (NVSR 75(5) p. 61).
  The open interval closes as NCHS closes it. NCHS sets `∞q100 = 1.0`,
  `∞d100 = l100` and `∞L100 = T100`, "the sum of the extrapolated Lx
  values for ages 100–120" (pp. 61–62), so the interval's life expectancy
  is `e100 = T100 / l100`. The target applies the group's ratio to the
  baseline as M-R6 does at single ages:
  `e100_T,g = e100_base × e100_g / e100_total`, where `e100_g` and
  `e100_total` divide the printed `Tx` by the printed `lx` in the "100 and
  older" rows of the group's and the total's tables, and
  `e100_base = life_expectancy(q_base(s, ·, t)[0..120], 100)`. For
  `other_non_hispanic`, `e100_T = e100_base × (e100_NHW / e100_total) /
  HR_85+`. **M-R7, open-interval central-rate scaling (assumption):**
  apply the 85+ NHIS hazard ratio to the NH white open-interval central
  rate before dividing by the source total's central rate and rescaling
  the baseline's central rate. This separate assumption equates that HR
  to a central-rate multiplier; constant force at single ages alone does
  not imply it. An open interval's central death rate is `l100 / T100 =
  1 / e100`, so this applies the source's ratio of open-interval death
  rates. Then `e65_T,g = (Σ_{a=65..99} L(a) + l(100) × e100_T,g) / l(65)`,
  which equals `life_table.py`'s backward recursion from 99 down to 65
  seeded with `e100_T,g`.
- **The model side, and the closing rule.** `e65_F,g =
  life_expectancy(q_F,g[0..120], 65)` for every group: the backward
  recursion with the constant-terminal-`q` closing at the last age
  (`life_table.py:17–37, 181–203`), applied to the fitted probabilities,
  whose race coefficients at 100–120 hold the age-99 value (§5). The
  module calls that closing "a builder default awaiting ratification"
  (lines 30–31); this record fixes it for the model side, the earnings
  targets and `e100_base` only. Target and model therefore close the top
  differently for race and Hispanic origin, so a mismatch in the tail
  reaches the residual instead of cancelling. No ruling this record cites
  prescribes the earlier construction, in which both sides shared the
  repository's tail: the design's §5.3 sets the 0.1-year limit, and the
  design mentions the closing only to call it "a builder-default
  constant-terminal-q closing rule that awaits ratification" (line 143;
  line 1146 repeats that §2.1 discloses it). So no sensitivity keeps that
  construction.
- **The limit.** `|e65_F,g − e65_T,g| ≤ 0.1` year, **the design's
  limit, which stays at 0.1 year** (design §5.3), for every earnings
  quintile and every race and Hispanic-origin group, both sexes, at every
  knot. Education has no e65 target: NCHS stops at 64 and S0.1 applies the
  limit to earnings groups and NCHS life-table targets; education's
  targets are contrasts under §9.1 and §9.3.

### 9.3 Uncertainty

S0.1 froze the requirements (§2.5): simultaneous 95 percent bounds,
Bonferroni over the family; NHIS resampling that respects strata, PSUs
and family clusters; ACS replicate weights for its denominators;
shared-source covariance; rounding, random variation, survey sampling and
linkage sensitivity kept apart; no independent-person bootstrap; no
complete-count rate treated as free of uncertainty. This record
implements them as four components, each reported on its own and then
combined.

| Component | Source | How the engine draws or computes it |
|---|---|---|
| U1, rounding and digitization | Every printed value; every digitized RMR | Uniform within the printing interval of §9.1, independently for each printed cell; uniform within `±δ_dig` for each digitized value |
| U2, random mortality variation | NCHS education | Poisson on the printed death counts: the `1/D` term of Formula 9 (NVSR 74(4) p. 132) and nothing else. Formula 9's ACS term `(SE(P)/P)²` enters through U3's replicate refits, so the ACS variance counts once |
| | NCHS life tables | Poisson with expected deaths `q_x × P_x`, where `P_x` is the group's population at age `x` in `R_ref(t)`. The life-table reports print no death counts, so this is a registered approximation, used at the Medicare-supplemented ages too. For the open interval (§9.2), Poisson on its central rate `1 / e100` with expected deaths `P_100+ / e100`, `P_100+` being the group's population at 100 and over in `R_ref(t)` |
| | OACT | **[open]** Study 129 prints rates and RMRs but no deaths or exposures (Tables 1–12), so the source cannot supply this component (row S2-24). It closes only through one of the three recorded routes below. Its direct and joint dependencies bar both earnings and race e65 members from passing while it stays open |
| U3, survey sampling | ACS (reference population and NCHS education denominators) | One refit per ACS replicate, with the variance formula that each year's PUMS documentation gives and the fit job records. NCHS's denominators move with the same replicate: each category's share within sex and band is re-tabulated from that replicate and scaled to NCHS's printed total. The fit job also reports the ratio of its replicate standard errors to NCHS's printed ones (Table VIII, I–19) |
| | NHIS–LMF | Rao–Wu rescaled bootstrap: PSUs resampled with replacement within strata, separately for each design period: the 2009 layout's `STRAT_P`/`PSU_P` and the 2016 and 2018 layouts' `PSTRAT`/`PPSU`, with the periods' strata kept distinct, as the 2018 survey description directs for pooled years: years within one design period pool as one, and different periods count as statistically independent, with distinct strata (pp. 92–93); the fit job reads which names each intervening year uses. Use family key `(SRVY_YR, HHX, FMX)` and person key `(SRVY_YR, HHX, FMX, FPX)`; survey description p. 71 defines the identifiers for within-year merges. Before resampling, check that each family nests in exactly one `(design_period, stratum, PSU)`, and keep all of each person's follow-up together. Never merge PSUs or strata. Failed nesting or fewer than two PSUs in any full-sample stratum stops the NHIS variance calculation under `SOURCE_UNAVAILABLE` (viii), and blocks education, race and SM2. For `n_h ≥ 2` PSUs, draw `n_h − 1` with replacement; a PSU drawn `m_hi` times takes multiplier `n_h m_hi / (n_h − 1)`. Use the full pooled sample's design units before subpopulation restriction, preserving zero-contribution PSUs. A singleton cannot yield an admitted zero variance. Survey description pp. 92–94 supports pooling 2009–2015 and 2016–2018 within their respective design periods and separating the periods, not merging units |
| U4, linkage and perturbation sensitivity | NHIS–LMF | Linkage: one discrete alternative fit, not draws, with NHIS weights replaced by the original sample-adult weight and ineligible persons dropped; the fit reports its conformance, and it does not gate. Perturbation: **[open]**, because public data cannot assess it. NCHS substituted synthetic data "for follow-up time or underlying cause of death for select records" and did not perturb vital status (LMF description p. 1), and the public data dictionary flags none of the altered records, so no public alternative can isolate the effect. The three closure routes below govern it; use of restricted-use linked files would first need an amendment to their exclusion (§3.4). Every NHIS target, every comparison using NHIS and every joint-fit product carries "public-file perturbation not assessed". Public data cannot size this component, so it enters no numeric bound; the dependency rule below carries it into verdicts. X-R1, which recodes `HISPAN_I` 10 and 11, is a crosswalk sensitivity (§8.2), not part of U4 |

**Component and residual dependencies [frozen here, coordinator's r2
ruling].** Treat LMF perturbation and OACT random variation component by
component and residual by residual. Separate reporting exempts neither
component when a required bound needs it. S0.1's rule (audit lines
661–669) keeps those members inconclusive until their components close;
a point residual outside tolerance still fails. Do not instead mark an
uncertain input target inconclusive merely because it is an input.

- **Every derived earnings e65 and every derived race/Hispanic-origin
  e65 member needs both components, absent a reviewed invariance proof.**
  The 150 earnings members and 120 race members (§9.4) use
  `q_F,g = q_base h_g / h_all`, and `h_g` averages the jointly normalized
  risks. The joint system is `F(β, w) = T_E,T_D,T_R` (§6.3), so locally
  `dβ = J⁻¹ dT` when the rank checks pass. The shared normalization and
  non-product `w(k,d,r)` give cross-dimension derivatives: a change in
  OACT's earnings targets can change race `h_g` with the race targets
  fixed. NHIS perturbation changes exposure, attained-age allocation and
  its fitted hazard targets (§4.5; LMF description p. 1); their change
  can change earnings single-age `h_g` while its band target stays fixed.
  A band-average constraint does not fix its single-age probabilities,
  and the e65 recursion uses those probabilities separately (§9.2).
  Race e65 has a direct NHIS dependency for the other group too. Thus
  neither freezing the other target nor reporting a component separately
  removes the joint dependency. The one-age and two-age invented
  fixtures in §11.7 exhibit the two directions; they prove no invariance.
- **Contrasts keep their reconstruction verdicts under one condition.**
  A successful refit must use exactly the same perturbed target on both
  sides of its reconstruction residual, at every imposing knot. Then
  `F_k(β*) − T_k = 0` to the fixed solver tolerance, for NHIS and OACT
  alike, and either missing component cancels from that residual. The
  same condition applies to NCHS reconstruction contrasts. Missing age
  identification, failed support/rank, a failed refit, an unmatched
  perturbation on the two sides or a changed estimand removes this
  exemption: keep the member in the family, label it unresolved under
  `SOURCE_UNAVAILABLE`/open identification or fail under
  `GATE_FAIL_OR_REGRESSION_FAIL` when the point residual fails. Never
  assume cancellation for an e65 residual.
- **Exactly three closure routes, by component and residual.** Before
  any outcome, a recorded amendment may (1) use uncertainty the source
  publishes, (2) use deaths or exposure the project obtains sufficient
  to construct the needed uncertainty, or (3) cite a reviewed invariance
  proof that removes the component's dependency from that residual over
  the full registered domain, including normalization, capping and
  tails. For OACT, (1) needs uncertainty/covariance for the fitted
  sex × band × quintile × year targets and derived bounds; (2) needs
  their death or exposure counts and the corresponding rate/exposure
  information; (3) must cover indirect race effects as well as any
  claimed earnings invariance. For LMF, (1) needs NCHS information sizing
  follow-up-time perturbation with shared-target dependence; (2) needs
  unperturbed deaths/exposures or a documented aggregate counterpart
  that identifies that component. Public totals alone do not separate
  synthetic follow-up. Restricted-use linked files remain excluded;
  that route would first need the exclusion amended. Route (3) must
  cover event exposure, attained age and both directions of joint
  propagation for each residual it exempts. An amendment names the
  person who chose the route, when they chose it and its evidence.
- **Run and publish while components stay open.** The fit does not wait
  for closure: run the supported steps and publish the residuals,
  numeric bounds conditional on included components, all omitted-component
  labels, and each dimension's status, subject to §4.5's identification
  limit and §11.5's suppression. A closure obtained after those outcomes
  cannot precede them: a verdict using it requires a new registered
  version in the lane's attempt ledger under
  `GATE_FAIL_OR_REGRESSION_FAIL`. Preserve the first attempt's published
  verdicts and ledger entries; nothing replaces them. The new version
  discloses which first-attempt residuals and bounds its authors had seen,
  and records who chose the closure route and when.
- **Consequence and hand-on.** Lifetime earnings, race and Hispanic
  origin, and SM2 as a whole cannot pass until every member's needed
  components close. Education keeps its separate reconstruction-conformance
  status, subject to every other rule, including the 85+ age limit.
  Every coefficient interval handed to SM3/SM4 names **both** omitted
  components: "OACT random variation not included" and "public-file
  perturbation not assessed", with any residual-specific invariance
  exemption named. **Reading for the next review:** an inconclusive SM2
  still hands on these labeled intervals; the scopes of
  `WEAK_POWER_OR_VACUITY` and `GATE_FAIL_OR_REGRESSION_FAIL` stay as §10
  states them. This reading authorizes no use that a failed gate blocks.
- **OACT Poisson sensitivity only.** Beside every affected e65 member,
  report a bound adding Poisson variation with expected deaths equal to
  the target probability times one fifth of that age's Social Security
  recipients of that sex in `R_ref(t)`, labeled "likely understates OACT's
  random variation": those recipients include beneficiaries OACT excludes
  (M-E4). It closes no component and changes no verdict. Study 129 versus
  Study 124 lacks this uncertainty too; report it without triggering
  `GRADIENT_SOURCES_INCONSISTENT` until its needed component closes.

**The engine.**

- **Monte Carlo draws** cover U1, U2 and NHIS's part of U3: `B = 2,000`
  draws, each a full refit of every knot and sex (§6.3) followed by every
  family member's residual. The seed is
  `numpy.random.SeedSequence(2026110101)`, spawned into one child stream
  per component and source in the order of §3's tables.
- **ACS replicates** cover the ACS part of U3: one refit per replicate,
  with the Monte Carlo inputs at their point values.
- **Component runs, reported only.** One joint Monte Carlo cannot show
  what each component contributes, so the fit also runs U1, U2 and NHIS's
  part of U3 one at a time: `B` draws of that component alone, from the
  same child stream the joint run uses, with every other input at its
  point value and a full refit per draw. The ACS replicate refits already
  isolate the ACS part of U3, and U4's alternative is a discrete fit. For
  every family member the fit reports each component's standard deviation
  beside the joint one. The component runs set no bound and change no
  verdict: the bound uses the joint draws and the ACS replicates, because
  capping and the tails make the response nonlinear, and the components'
  variances then need not add up to the joint variance.
- **Combination.** For family member `k`,
  `SD_k = sqrt(Var_MC,k + Var_ACS,k)`, treating ACS sampling as independent
  of the other components. NCHS's education denominators are ACS too, and
  they sit inside `Var_ACS` with the reference population.
- **Shared-source covariance.** Each draw perturbs each printed source
  value once, and every target, refit and e65 in that draw uses that same
  value: the `q3` RMR enters four contrasts; an NH white `qx` enters two
  race contrasts and every race e65 target; an ACS replicate enters the
  reference population and NCHS's denominators together.
- **Separate endpoints and approximation guard.** For each member set
  `z = Φ⁻¹(1 − 0.025 / 6,884) ≈ 4.486`, `γ` to the sample skewness
  of its Monte Carlo residuals, and `S = sqrt(Var_MC + Var_ACS)`.
  For each `u ∈ {−z, +z}`, set `c(u, γ) = u + (u² − 1)γ/6`.
  The lower endpoint is `r̂ + S c(−z, γ)`; the upper endpoint is
  `r̂ + S c(+z, γ)`. Always compute both; never use one corrected
  quantile as a symmetric half-width. For exactly constant Monte Carlo
  residuals take `γ = 0`; keep any ACS variance in `S`.
  Freeze the validity guard to finite inputs, `|γ| z < 3`, and explicit
  `c(−z, γ) < 0 < c(+z, γ)` and lower ≤ upper. The skewness guard
  makes the first-order quantile map strictly increasing throughout
  `[−z, z]`, since its derivative is `1 + γu/3`. This is an operational
  domain for the approximation, not a coverage theorem. Outside it a
  member is inconclusive, never a pass; do not clip or reorder endpoints.
  **First-order Cornish–Fisher alone does not establish nominal
  Bonferroni coverage.** These are approximate, component-conditional
  residual bounds using the nominal 95 percent Bonferroni allocation,
  under the registered resampling and mapping assumptions. They claim
  propagation of the included components under that approximation, not
  certified 95 percent repeated-sample family coverage. A claim that
  requires nominal coverage remains open unless a reviewed pre-outcome
  coverage argument justifies it; the approximation alone cannot confer
  that claim or a pass requiring it. Report the guard and this limitation
  with each bound. Missing-component rules below apply independently.
- **Monte Carlo error of each endpoint.** Use a delete-one-draw
  jackknife, recomputing `S`, `γ` and `c` with ACS variance fixed, for
  lower and upper separately. For endpoint `E`, with leave-one-out
  endpoints `E_(b)` and their mean `Ē`,
  `SE_MC(E) = sqrt((B − 1)/B × Σ_b (E_(b) − Ē)²)`.
  This includes uncertainty in skewness and SD; `r̂` is the deterministic
  point-fit residual and stays fixed. Every leave-one-out sample must
  pass the same validity guard. Require **each** endpoint's SE below
  `τ_k / 10`: less than 0.01 year for e65 and `ε / 10` for a contrast.
  If either error exceeds its limit or a leave-one-out guard fails,
  double `B`, up to 32,000. At exhaustion the member is inconclusive;
  a full-sample validity failure is immediately inconclusive. Tier A
  carries no simulation error. Point residuals outside tolerance fail
  even when the procedure cannot establish endpoint validity or precision.

### 9.4 The critical family: 6,884 targets [frozen here]

| Block | Count | Tolerance `τ` |
|---|---:|---|
| OACT contrasts (M-E1): 63 observed band-years in 2010–2022 (four bands × 13 years, 80–84 × 8, 85–89 × 3) × 2 sexes × 4 quintiles | 504 | ε |
| e65 by earnings quintile: 5 × 2 sexes × 15 knots | 150 | 0.1 year |
| NCHS education contrasts (M-D1, M-D2): 5 years × 2 sexes × 4 bands × 2 contrasts | 80 | ε |
| NHIS education contrasts at 65+ (M-D4): 3 × 3 bands × 2 sexes | 18 | ε |
| NHIS `college`/`some_college` split (M-D3): 2 sexes | 2 | ε |
| NCHS race contrasts (M-R1): 2 groups × 100 ages × 2 sexes × 15 years | 6,000 | ε |
| e65 by race and Hispanic-origin group: 4 × 2 sexes × 15 knots | 120 | 0.1 year |
| NHIS `other_non_hispanic` contrasts (M-R4): 5 bands × 2 sexes | 10 | ε |
| **Total** | **6,884** | |

**Machine-readable member groups.** These are the same eight groups,
including every unavailable or unidentified member. Contrast kinds below
mean the same-target successful-refit condition of §9.3. Counts here
count quantities, never source table values.

```json
{"sm2_member_groups": [
    {
      "source": "OACT",
      "dimension": "lifetime_earnings",
      "kind": "oact_contrast",
      "knots_or_ages": "63 observed band-years, 2010–2022; six bands 62–89; two sexes, four contrasts",
      "count": 504
    },
    {
      "source": "OACT",
      "dimension": "lifetime_earnings",
      "kind": "earnings_e65",
      "knots_or_ages": "2010–2024; age 65; five quintiles, two sexes",
      "count": 150
    },
    {
      "source": "NCHS",
      "dimension": "education",
      "kind": "nchs_education_contrast",
      "knots_or_ages": "2018–2022; four bands 25–64; two sexes, two contrasts",
      "count": 80
    },
    {
      "source": "NHIS",
      "dimension": "education",
      "kind": "nhis_education_contrast",
      "knots_or_ages": "pooled; 65–74, 75–84, 85+; three contrasts, two sexes; six 85+ members unidentified",
      "count": 18
    },
    {
      "source": "NHIS",
      "dimension": "education",
      "kind": "nhis_split_contrast",
      "knots_or_ages": "pooled; 25–64; two sexes",
      "count": 2
    },
    {
      "source": "NCHS",
      "dimension": "race_hispanic_origin",
      "kind": "nchs_race_contrast",
      "knots_or_ages": "2010–2024; ages 0–99; two groups, two sexes",
      "count": 6000
    },
    {
      "source": "NCHS+NHIS",
      "dimension": "race_hispanic_origin",
      "kind": "race_e65",
      "knots_or_ages": "2010–2024; age 65; four groups, two sexes",
      "count": 120
    },
    {
      "source": "NHIS",
      "dimension": "race_hispanic_origin",
      "kind": "nhis_other_contrast",
      "knots_or_ages": "pooled; 25–44, 45–64, 65–74, 75–84, 85+; two sexes; two 85+ members unidentified",
      "count": 10
    }
  ]
}
```

- **Component eligibility.** Each of the 150 earnings e65 and 120 race
  e65 members needs both OACT random variation and LMF perturbation
  through §9.3's joint dependency rule, until a recorded closure or
  reviewed residual-specific invariance amendment removes that need.
  Successful same-target reconstruction contrasts retain their verdicts;
  unavailable ages/inputs and point failures still cannot pass. Publish
  supported residuals and component-labeled bounds while components stay
  open. A closure after outcomes requires the new registered ledger
  version of §9.3, preserving first verdicts. Section 9.7 computes counts
  with other issues resolved, without changing this family.
- **Joint-survey targets.** The 30 NHIS targets are in the family; they
  are the only targets whose estimates this project computes from survey
  records. NCHS's education rates also rest on a survey, through their
  ACS denominators (§3.2), and U3 carries that sampling error (§9.3).
- **One member per published or estimated quantity.** A target imposed at
  several knots (a backcast copy, a held target or an NHIS target) is one
  member, tested by its largest absolute residual across the knots that
  impose it. The e65 targets differ by knot, because the baseline does, so
  each knot's is a member.
- **What the contrast members test.** For a contrast, the residual is the
  model-implied contrast minus the draw's target after that draw's refit.
  Under §6.3's support/rank checks and the same-target successful-refit
  condition (§9.3), a contrast member shows whether every refit
  reproduces its targets: a
  reconstruction check. The
  e65 members compare two different constructions (the model on the
  reference population against the source's ratios on the baseline), so
  they also test composition, capping and tails. For earnings that test
  is narrow: with `Q̃`'s exact fifths among recipients at 62–89 (§6.2),
  each earnings e65 member checks chiefly whether its band's five printed
  RMRs average to one, plus capping, the spread of composition across the
  band's single ages, and the tail above 89. The race and
  Hispanic-origin e65 members also test the model's tail against NCHS's:
  their targets close the "100 and older" interval as NCHS does, while the
  model keeps the repository's closing (§9.2).
- **What the contrast members cost.** The 6,614 contrast members under the same-target successful-refit
  condition carry no residual source uncertainty; numerical failure and
  identification limits still apply. Their inclusion raises the Bonferroni constant for the 270 e65
  members from `Φ⁻¹(1 − 0.025 / 270) ≈ 3.738` to about 4.486, which makes
  those bounds about 20 percent wider; the family still follows S0.1's
  definition (audit lines 657–659), and this record leaves it unchanged.
- **Not in the family.** The sensitivities of §5, §6.5, §7.3 and §8.2, and the
  sources reported beside the fit.

### 9.5 Pass conjunction

SM2 earns admission, labeled "calibrated, not validated", only if all
of these hold:

1. every tier A check passes (§9.1);
2. every one of the 6,884 members has its residual bound inside `±τ_k`,
   with §9.3's endpoint validity/error and needed-component requirements
   met; an approximation alone cannot establish required nominal coverage;
3. every invariant of §9.6 holds;
4. no condition in §10 blocks.

A member whose point residual lies inside `±τ_k` but whose bound crosses
it is **inconclusive**; a member whose point residual lies outside fails.
An inconclusive member makes its dimension inconclusive (e65 by quintile
and OACT contrasts: lifetime earnings; education contrasts: education;
race contrasts, race e65 and `other_non_hispanic`: race and Hispanic
origin). **A bound too wide to judge never passes.** The record publishes
each dimension's status; SM2 passes as a whole only when all three pass,
because SM1 needs all three. Every derived earnings and race e65 member
needs OACT random variation and LMF perturbation through the joint fit,
unless a reviewed invariance amendment removes that dependency (§9.3).
While either needed component stays open, such a member is inconclusive
or fails whatever its numeric bound, so lifetime earnings, race and
Hispanic origin, and SM2 cannot pass. Education retains its own
reconstruction-conformance status subject to all other findings; §4.5's
six education and two race 85+ members cannot pass under option (b).
Every failed, unavailable or unidentified member stays in the 6,884-member
conjunction. Endpoint invalidity or inadequate endpoint precision cannot
turn an inconclusive member into a pass. A disagreement trigger removes
competing sources from fitted roles as §10 requires; that removal never
shrinks the family or earns admission.

### 9.6 Invariants (design §6)

- **Life tables.** Every fitted group life table (`q_F,g` for each knot,
  sex and group) satisfies `data/life_table.py`'s invariants:
  `period_life_table` and `life_expectancy` agree, both with `f0 = 0.5`,
  the uniform-deaths convention the module applies at every other age
  (`life_table.py:13`); `f0` moves only `L0` and `e0` (lines 143 and
  173–177), which no SM2 quantity reads; survivorship and
  remaining person-years `Tx` are nonnegative and nonincreasing with age;
  interval person-years `Lx` are nonnegative; changing the
  radix changes no life expectancy; raising any `q` cannot raise life
  expectancy at an earlier age (`life_table.py:39–51`).
- **Registered ordering.** For each sex and knot: if the earnings e65
  targets rise strictly from `q1` to `q5`, the fitted e65 must rise the
  same way; if the targets do not (Study 129 reports exceptions for women
  at 62–64 in a few years between 1995 and 2010, p. 8), the check reports
  "source unordered" and does not fail. NHIS's education hazards at 65+
  follow the
  same rule (`less_than_high_school` ≥ `high_school` ≥ `some_college` ≥
  `college` in the targets implies the same in the fit). Race and
  Hispanic origin carry no registered ordering.
- **Permutation invariance.** Refitting with every input table's rows
  and the reference population's rows permuted gives coefficients equal
  within `1 × 10⁻¹²` in log units.
- **SM1.** Each table passes `RelativeRiskSpec`; SM1's cell conservation
  holds on `R_ref` at every knot; SM1's own test modules pass unchanged.

### 9.7 Eligibility while components stay open

These count **eligibility to pass**, considering each component with all
other issues resolved, including age identification, source availability,
endpoint validity and the same-target successful-refit condition. Actual
point failures remain failures. No real-data verdict enters these counts.
They follow §9.3's needed-bound rule, not an input-target override.
Option (b)'s eight unidentified 85+ contrasts remain in the member list;
they cannot pass the actual conjunction (§9.5), but these component-only
counts resolve that separate issue by definition.

<!-- sm2-eligibility-table:start -->
| Open component(s) | Dimension | Cannot pass | Still eligible |
|---|---|---:|---:|
| OACT random variation | lifetime_earnings | 150 | 504 |
| OACT random variation | education | 0 | 100 |
| OACT random variation | race_hispanic_origin | 120 | 6010 |
| OACT random variation | **Total** | **270** | **6614** |
| LMF perturbation | lifetime_earnings | 150 | 504 |
| LMF perturbation | education | 0 | 100 |
| LMF perturbation | race_hispanic_origin | 120 | 6010 |
| LMF perturbation | **Total** | **270** | **6614** |
| OACT random variation + LMF perturbation | lifetime_earnings | 150 | 504 |
| OACT random variation + LMF perturbation | education | 0 | 100 |
| OACT random variation + LMF perturbation | race_hispanic_origin | 120 | 6010 |
| OACT random variation + LMF perturbation | **Total** | **270** | **6614** |
<!-- sm2-eligibility-table:end -->

The generator reads §9.4's member groups from the path argument and
stores no family or dimension count in code. Its dependency function uses
source, dimension and kind. The test states its case table separately
from §9.3's prose: reconstruction contrasts need neither component under
the cancellation condition; both e65 kinds need both components. It
checks exact table reproduction and family total, every subset's
partition by dimension, monotonicity when components close, the union of
barred members, contrast cancellation, every kind's dependencies, and
Hypothesis-drawn invented lists against member-by-member enumeration.
Hypothesis uses no database or deadline and omits `Phase.explain`.

**CI does not run these blocks.** Any amendment to the member list must
extract and rerun them. From the repository root the exact extraction
command is:

```bash
.venv/bin/python -I -B - <<'PYEXTRACT'
from pathlib import Path
import re
record = Path('docs/design/mortality_ses_sm2_freeze.md').read_text()
out = Path('.sm2-fix2-scratch/eligibility')
out.mkdir(parents=True, exist_ok=True)
pattern = r'^```python\n(# sm2-eligibility: (generator|test)\n.*?)^```$'
blocks = {kind: code for code, kind in re.findall(pattern, record, re.M | re.S)}
assert set(blocks) == {'generator', 'test'}
for kind, name in [('generator', 'eligibility.py'), ('test', 'test_eligibility.py')]:
    (out / name).write_text(blocks[kind])
PYEXTRACT
```

Then, from `.sm2-fix2-scratch/eligibility/`, run:

```bash
../../.venv/bin/python -I -B -m pytest -q -p no:cacheprovider --noconftest -c /dev/null --rootdir=. --basetemp=../pt test_eligibility.py
```

```python
# sm2-eligibility: generator
import json
import re
import sys
from pathlib import Path

COMPONENTS = ("OACT random variation", "LMF perturbation")
DIMENSIONS = ("lifetime_earnings", "education", "race_hispanic_origin")


def dependencies(source, dimension, kind):
    """Same-target successful-refit reconstruction contrasts only."""
    contrasts = {
        ("OACT", "lifetime_earnings", "oact_contrast"),
        ("NCHS", "education", "nchs_education_contrast"),
        ("NHIS", "education", "nhis_education_contrast"),
        ("NHIS", "education", "nhis_split_contrast"),
        ("NCHS", "race_hispanic_origin", "nchs_race_contrast"),
        ("NHIS", "race_hispanic_origin", "nhis_other_contrast"),
    }
    if (source, dimension, kind) in contrasts:
        return frozenset()
    if (source, dimension, kind) in {
        ("OACT", "lifetime_earnings", "earnings_e65"),
        ("NCHS+NHIS", "race_hispanic_origin", "race_e65"),
    }:
        return frozenset(COMPONENTS)
    raise ValueError("Unregistered member kind/source/dimension")


def read_groups(path):
    record = Path(path).read_text()
    match = re.search(r"```json\n(\{\"sm2_member_groups\".*?\})\n```", record, re.S)
    groups = json.loads(match.group(1))["sm2_member_groups"]
    for group in groups:
        if not isinstance(group["count"], int) or group["count"] < 0:
            raise ValueError("Invalid member count")
        dependencies(group["source"], group["dimension"], group["kind"])
    return groups


def grouped_counts(groups, opened):
    counts = {dimension: [0, 0] for dimension in DIMENSIONS}
    for group in groups:
        needs = dependencies(group["source"], group["dimension"], group["kind"])
        barred = bool(needs & set(opened))
        counts[group["dimension"]][0 if barred else 1] += group["count"]
    return counts


def markdown(groups):
    lines = ["| Open component(s) | Dimension | Cannot pass | Still eligible |",
             "|---|---|---:|---:|"]
    scenarios = [(component,) for component in COMPONENTS] + [COMPONENTS]
    for opened in scenarios:
        label = " + ".join(opened)
        counts = grouped_counts(groups, opened)
        for dimension, (barred, eligible) in counts.items():
            lines.append(f"| {label} | {dimension} | {barred} | {eligible} |")
        barred = sum(pair[0] for pair in counts.values())
        eligible = sum(pair[1] for pair in counts.values())
        lines.append(f"| {label} | **Total** | **{barred}** | **{eligible}** |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    print(markdown(read_groups(sys.argv[1])), end="")
```

```python
# sm2-eligibility: test
import importlib.util
import itertools
import re
from pathlib import Path

import pytest
from hypothesis import Phase, given, settings, strategies as st

HERE = Path(__file__).resolve().parent
RECORD = HERE.parent.parent / "docs/design/mortality_ses_sm2_freeze.md"
spec = importlib.util.spec_from_file_location("sm2_eligibility", HERE / "eligibility.py")
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)
OACT, LMF = "OACT random variation", "LMF perturbation"
# Independent case table from §9.3's prose, one row per member kind.
CASES = [
    ("OACT", "lifetime_earnings", "oact_contrast", ()),
    ("OACT", "lifetime_earnings", "earnings_e65", (OACT, LMF)),
    ("NCHS", "education", "nchs_education_contrast", ()),
    ("NHIS", "education", "nhis_education_contrast", ()),
    ("NHIS", "education", "nhis_split_contrast", ()),
    ("NCHS", "race_hispanic_origin", "nchs_race_contrast", ()),
    ("NCHS+NHIS", "race_hispanic_origin", "race_e65", (OACT, LMF)),
    ("NHIS", "race_hispanic_origin", "nhis_other_contrast", ()),
]
EXPECTED = {case[:3]: set(case[3]) for case in CASES}
SUBSETS = [set(subset) for size in range(3)
           for subset in itertools.combinations((OACT, LMF), size)]


def enumerate_members(groups, opened):
    counts = {dimension: [0, 0] for dimension in generator.DIMENSIONS}
    for group in groups:
        needs = EXPECTED[group["source"], group["dimension"], group["kind"]]
        for _ in range(group["count"]):
            counts[group["dimension"]][0 if needs.intersection(opened) else 1] += 1
    return counts


def barred_ids(groups, opened):
    return {(index, member) for index, group in enumerate(groups)
            if generator.dependencies(group["source"], group["dimension"], group["kind"]) & opened
            for member in range(group["count"])}


def test_record_table_and_total():
    record = RECORD.read_text()
    groups = generator.read_groups(RECORD)
    printed = record.split("<!-- sm2-eligibility-table:start -->\n", 1)[1].split(
        "<!-- sm2-eligibility-table:end -->", 1)[0]
    assert printed == generator.markdown(groups)
    total = re.search(r"### 9\.4 The critical family: ([\d,]+) targets", record).group(1)
    assert sum(group["count"] for group in groups) == int(total.replace(",", ""))


@pytest.mark.parametrize("source,dimension,kind,expected", CASES)
def test_dependency_cases(source, dimension, kind, expected):
    assert generator.dependencies(source, dimension, kind) == set(expected)


def test_every_subset_partition():
    groups = generator.read_groups(RECORD)
    totals = {dimension: sum(group["count"] for group in groups
                             if group["dimension"] == dimension)
              for dimension in generator.DIMENSIONS}
    for opened in SUBSETS:
        counts = generator.grouped_counts(groups, opened)
        assert counts == enumerate_members(groups, opened)
        for dimension, (barred, eligible) in counts.items():
            assert barred + eligible == totals[dimension]


def test_closing_monotonic_and_union():
    groups = generator.read_groups(RECORD)
    for opened in SUBSETS:
        for closed in SUBSETS:
            if closed <= opened:
                assert barred_ids(groups, closed) <= barred_ids(groups, opened)
                a = generator.grouped_counts(groups, closed)
                b = generator.grouped_counts(groups, opened)
                for dimension in generator.DIMENSIONS:
                    assert a[dimension][0] <= b[dimension][0]
    assert barred_ids(groups, {OACT, LMF}) == (
        barred_ids(groups, {OACT}) | barred_ids(groups, {LMF}))
    # Count the union member by member; catches intersection aggregation.
    union = barred_ids(groups, {OACT}) | barred_ids(groups, {LMF})
    counts = generator.grouped_counts(groups, {OACT, LMF})
    for dimension in generator.DIMENSIONS:
        assert counts[dimension][0] == sum(
            groups[index]["dimension"] == dimension for index, _ in union)


def test_contrasts_never_barred():
    groups = [group for group in generator.read_groups(RECORD)
              if group["kind"].endswith("_contrast")]
    for opened in SUBSETS:
        assert not barred_ids(groups, opened)
        assert all(barred == 0 for barred, _ in generator.grouped_counts(groups, opened).values())


@st.composite
def invented_groups(draw):
    cases = draw(st.lists(st.sampled_from(CASES), min_size=0, max_size=20))
    return [dict(source=source, dimension=dimension, kind=kind,
                 count=draw(st.integers(min_value=0, max_value=40)),
                 knots_or_ages="invented") for source, dimension, kind, _ in cases]


@settings(database=None, deadline=None,
          phases=(Phase.explicit, Phase.generate, Phase.shrink))
@given(invented_groups())
def test_grouped_equals_enumeration(groups):
    for opened in SUBSETS:
        assert generator.grouped_counts(groups, opened) == enumerate_members(groups, opened)
```

## 10. Named conditions

This record fixes every fallback below now, before any outcome. **Nobody
tunes anything so that sources agree** (S0.1 §2.5, frozen).

| Condition | Trigger for SM2 | What it stops | Fallback |
|---|---|---|---|
| `GRADIENT_SOURCES_INCONSISTENT` | Two comparable sources disagree beyond SM2's fit tolerance. "Comparable": the same SM category definitions and sex, overlapping ages, calendar windows that overlap at least half the shorter one, and populations that differ at most in institutional coverage. Assessed: (a) Study 129 against Study 124 at table years 1995–2015, bands 62–84; (b) NCHS life tables against NHIS–LMF for `hispanic` and `black_non_hispanic` at 25–84; (c) NCHS education for 2018 and 2019, the two fitted NCHS years inside NHIS's 2009–2019 window, against NHIS–LMF at 25–64, compared year by year as (b) compares, with NHIS's estimator (§4.5) run at attained ages 25–64 by sex and with `some_college` and `college` pooled into one category to match M-D2. Not assessed: OACT against Cristia (different years, ages and earnings measures), and `other_non_hispanic` against the partial composite (different groups). Metric: the difference in temporary life expectancy over the pair's shared ages, each built by applying the source's ratios to the TR 2026 baseline of the year compared: for (a), from 62 to the top of the year's oldest band printed in both studies, per table year, sex and quintile (5 × 2 × 5 = 50 comparisons); for (b), from 25 to 85, per NCHS year 2010–2019, sex and group (10 × 2 × 2 = 40); for (c), from 25 to 65, per NCHS year, sex and contrast (`less_than_high_school` and `some_college_or_more`, each against `high_school`; 2 × 2 × 2 = 8). NHIS's hazard ratios act on the baseline's hazard, `q = 1 − (1 − q_base)^HR` (M-D4's constant-force mapping). Triggered when a comparison's simultaneous 95 percent bound, Bonferroni over these 98 comparisons (`z = Φ⁻¹(1 − 0.025 / 98) ≈ 3.475`), excludes ±0.1 year, using §9.3's separate endpoints, validity/error checks and coverage limitation with this comparison-family critical value | Apply S0.1's frozen consequence (audit 694–696; design 905): OACT stays primary and all competing sources become registered sensitivities. Remove NCHS and NHIS from every fitted role, including NHIS education 65+, the split and the other group. The required education/race targets then lack a fitted source: JR-C, those dimensions and SM2 stop under `SOURCE_UNAVAILABLE`, open identification. Keep every family member and publish the trigger and the stopped statuses. Pair (a) lacks its random-variation component (§9.3), so report its comparison without a trigger until that dependency closes | Competing-source products run only as labeled registered sensitivities; none supplies a fallback fitted role |
| `SOURCE_UNAVAILABLE` | (i) The digitization fails validation, or the digitizer cannot read a figure; (ii) an NHIS or LMF file is missing or its hash differs; (iii) an ACS year is missing; (iv) the ordered logit does not converge for some knot, sex or ACS replicate (§6.2); (v) any source file's hash differs from §13 or the fit job's manifest (the ACS documents of §13.6 follow §6.2's text rule instead); (vi) no ACS year's income-item documents pass §6.2's acceptance rule; (vii) an NCHS report/table file that §3 lists is missing or fails its layout; (viii) unidentified NHIS open-band ages, invalid dates, failed support/rank/derivatives, failed family nesting or a full-sample singleton (§4.5, §6.3, §9.3); or the disagreement consequence removes a required fitted source | (i) P-PRIMARY, and with it SM2's admission; (ii) admission of education and race; (iii) one missing year: nothing, the knot uses the nearest observed ACS year, the earlier one on a tie, labeled; two or more: SM2's admission; (iv) JR-C, and with it SM2's admission; (v) the run; (vi) JR-C, and with it SM2's admission (a year that fails alone only borrows `λ`, labeled, §6.2); (vii) any missing required NCHS year blocks its dimension and SM2: every missing contrast stays in the family, inconclusive, and every dependent e65 stays inconclusive. In particular a missing frozen last-observed source cannot shift Q6 to an earlier year. This tighter rule removes fix round 1's interior-year admission fallback as well. (viii) the affected estimator/knot/replicate and dimension, JR-C when it cannot form a complete table, and SM2; no dropping members or rank-deficient columns | (i) P-TABLE, computed and published labeled, never substituted; the Q6 question goes to Max (§12). (ii) T-D1 for education at 65+, Cristia's conditional `college`/`some_college` contrast for the split, T-R2 for `other_non_hispanic` at 2019–2024, with knots 2010–2018 taking the 2019 composite by §7.5's hold-first rule, labeled "partial group, held back from 2019", so no knot falls to a default zero; all labeled, none admitted. (iv) and (vi) JR-B, labeled, not admitted. (vii) an earlier-year product only as a labeled sensitivity pending an amendment; Q6's primary stays frozen. (viii) §4.5/§10's supported estimates and diagnostic sensitivities only, with no admitted complete primary; none retains a competing source in a fitted role after disagreement |
| `EXPOSURE_UNRESOLVED` | Any report calls a comparison with a source reported beside the fit out of sample or a holdout, or describes a later role as blind to these sources | That claim | None: every SM2 source is an exposed target (§1) |
| `FRAME_ATTRIBUTE_MISSING` | A frame that would use SM2's coefficients lacks a dimension's column; the Microcosm frame lacks education (design §7.2) | Use of the coefficients on that frame; closed-cohort work continues, labeled | None. The reference population's missing lifetime earnings is a declared proxy (§6.2), not this condition |
| `SMALL_CELL_DISCLOSURE` | A published aggregate from NHIS or ACS microdata rests on fewer than 100 unweighted persons, or a published death-based cell on fewer than 20 deaths (§11.5) | Publication of that artifact until the writer suppresses the cell and any complement that reveals it | Suppression |
| `CELL_CONSERVATION_BROKEN` | SM1's cell log on `R_ref` at any knot shows an infeasible cell, or a feasible cell that does not conserve deaths | SM2's admission | None |
| `GATE_FAIL_OR_REGRESSION_FAIL` | A tier A check fails; a family member's point residual lies outside `±τ`; a knot's calibration fails to converge or its prescribed starts disagree (§6.3); an invariant fails; an SM1 test regresses | SM2's admission and everything resting on it: SM3's registration on these coefficients and SM4's use of them. The fit publishes the result with no seed selection and no tolerance relief; a new attempt needs a new registered version and enters the lane's attempt ledger (design §8) | None |
| `WEAK_POWER_OR_VACUITY` | A family member is inconclusive (§9.5), which includes each derived earnings or race e65 member while either needed OACT/LMF component stays open, and each unidentified 85+ member (§4.5, §9.3); or a report presents the contrast members' pass, which reproduces inputs by construction, as evidence that the gradients are right | The affected dimension's admission, and with it SM2's admission as a whole (§9.5); the claim | None. SM2 makes no 0.90-power claim (S0.1 §2.5). The fit still publishes every residual, bound and dimension status, except what §11.5 withholds |

## 11. Build plan

### 11.1 When the fit job starts

**The fit job starts only after this record merges.** Its brief and its
first commit cite the merge commit and this file's blob hash at that
commit (`git rev-parse <merge>:docs/design/mortality_ses_sm2_freeze.md`),
and it refuses to run if the file at its base differs. Any change to a
frozen item after the merge needs a recorded amendment and a fresh review
round, as S0.1's header requires.

### 11.2 What it builds, in order

All new modules sit under `src/populace_dynamics/mortality_ses/`. SM1's
modules stay unchanged: the `CoefficientPath` protocol,
`HoldLastCoefficientPath`, `RelativeRiskSpec` and `normalize_probabilities`
cover every interface SM2 needs (design §5.1: a new module and a new
registered version per milestone).

1. **`sources.py`.** The source registry: for each input, its publisher,
   title, release date, URL, retrieval date, byte size, SHA-256, and the
   tables and pages used. Every reader checks the hash first and refuses a
   mismatch.
2. **`extract_oact.py`.** Two independent transcriptions of Study 129
   Tables 1–12 and Study 124 Tables 4–8, and their reconciliation; the
   Figures 7–12 vector digitizer with its 210-point validation (§7.2).
3. **`extract_nchs.py`.** Two independent transcriptions of the education
   tables (2018–2022, and 2010–2017 for E-S1) and the life tables
   (2010–2024).
4. **`nhis_lmf.py`.** Readers for the NHIS 2009–2018 sample-adult and
   person files and the LMF files, the harmonization of §3.4 and §8.2, the
   estimator of §4.5 and the Rao–Wu bootstrap of §9.3. Its estimates
   pass to the fit in memory, inside the one registered run (item 10),
   and never leave it; only the run's published artifact leaves it, and
   every NHIS- or LMF-derived cell there meets §11.4 and §11.5.
   Suppression acts on that output alone, so the fit never consumes a
   suppressed value.
5. **`reference_population.py`.** The ACS reader, the crosswalks, `Q̃`, the
   ordered logit and `R_ref(t)` with its replicates (§6.2). The
   calibration reads `R_ref(t)`'s full cell weights in memory, inside the
   same run; suppression applies only to what the run publishes (§11.5).
6. **`targets.py`.** The mappings of §4: extracted values to targets, with
   printing intervals and assumption labels.
7. **`joint_fit.py`.** The calibration of §6.3, and the JR-A, JR-B, JR-D,
   JR-E and scaled-`λ` routes.
8. **`paths.py`.** P-PRIMARY, P-TABLE, P-PRE, E-S1 and
   `WideningCoefficientPath` (§7).
9. **`conformance.py`.** §9 in full, and the comparisons of §10.
10. **`scripts/run_sm2_fit.py`**, one registered entry point that writes
    one new artifact (an exclusive output path, with an abort record if it
    stops), and **`docs/design/mortality_ses_sm2_fit.md`**, the fit's
    design note with its invariants.

### 11.3 The extracted-table format

One CSV per source table or figure, and a JSON sidecar holding the
source's registry entry. Columns:

| Column | Content |
|---|---|
| `source_id`, `source_sha256` | Registry key and the file's hash |
| `table_or_figure`, `pdf_page`, `printed_page` | Locator |
| `row_label`, `column_label`, `category_source` | Verbatim strings from the source |
| `category_sm`, `sex`, `age_lower`, `age_upper`, `year` | Mapped keys (§8.2) |
| `quantity` | One of `rmr`, `death_rate`, `qx`, `rate_per_100000`, `deaths`, `population`, `standard_error`, `odds_ratio`, `z_statistic`, `mortality_ratio`, `lx`, `Tx` |
| `printed_string`, `value`, `decimals`, `half_width` | The string as printed, its parsed value, its printed decimals and its printing (or digitization) half-width |
| `age_interval`, `interval_width`, `age_label_printed` | `single_age`, `closed_band` or `open`; a positive width for a finite interval and null for open. An open interval has `age_upper = null`, `age_lower = 100` and the source's printed age-label string. Never encode it as an annual probability at age 100 |
| `quantity_units`, `radix`, `provenance_id` | Units of `lx` and `Tx`, the table's radix identifier, and a link to the sidecar's source hash, page and transcription provenance. Pair `lx` and `Tx` only within the same table, sex, year, open interval and radix |
| `method`, `reader_version` | `text_layer_a`, `text_layer_b` or `vector_digitized`, and the tool version |
| `transcription_check`, `validation_residual` | Whether the two transcriptions agree; for digitized values, the residual at validation points |
| `assumption_labels` | The §4–§7 labels that apply (for example `M-E2;BAND_BACKCAST_HOLD_FIRST`) |

### 11.4 How microdata stays out of the repository and out of a job's context

- NHIS, LMF and ACS microdata live outside every repository, worktree,
  scratch folder and Subfleet job folder, under one data directory that Max
  names. Code finds it through the environment variable
  `SM2_MICRODATA_ROOT`, and no prompt to a lane that may open workspace
  files names that path.
- No agent displays a record: no `head`, `tail`, `cat`, `less`, sample,
  `print(df)` or row indexing of a microdata file, and no per-person value
  in a log, test output, fixture, commit, PR body, issue comment or prompt.
- Readers catch every exception and re-raise it without row content.
- Every output that reaches an agent is an aggregate over at least two
  records; anything published also meets §11.5.
- Tests use synthetic fixtures built from the layouts, never survey
  records.
- Runs on real microdata go through the registered entry point on a
  machine that holds the data directory, and print aggregates only.

### 11.5 Suppression rule

Every published aggregate derived from NHIS, LMF or ACS microdata rests on
at least **100 unweighted persons** (the SSA MINT8 Table User Guide's
"Sample Size Restrictions" minimum that S0.1 cites), and every published
death-based cell on at least **20 deaths** (NCHS's own threshold for
showing a rate, NVSR 74(4) p. 132). The writer suppresses a cell below
either floor together with every complement that would reveal it by
subtraction, and refuses an artifact that still holds one. This is a
publication rule, not a precision guarantee (S0.1 §2.5).

**An NHIS target below a floor.** A target whose estimate rests on fewer
than 100 unweighted persons or 20 deaths stays in the fit and in the
critical family: the run computes its residual and bound in memory, and
the artifact publishes its verdict (pass, inconclusive or fail) and
withholds its value, standard error, bound and residual, together with
every complement that would reveal them.

### 11.6 Public files to download

| Files | URL | Checked in this job |
|---|---|---|
| Study 129, Study 124 | https://www.ssa.gov/oact/NOTES/pdf_studies/study129.pdf, https://www.ssa.gov/OACT/NOTES/pdf_studies/study124.pdf | Bytes in S0.1's source folder at the hashes in §13 |
| US Life Tables 2010–2024 | Under https://www.cdc.gov/nchs/data/nvsr/: `nvsr63/nvsr63_07.pdf` (2010), `nvsr64/nvsr64_11.pdf` (2011), `nvsr65/nvsr65_08.pdf` (2012), `nvsr66/nvsr66_03.pdf` (2013), `nvsr66/nvsr66_04.pdf` (2014), `nvsr67/nvsr67_07-508.pdf` (2015), `nvsr68/nvsr68_04-508.pdf` (2016), `nvsr68/nvsr68_07-508.pdf` (2017), `nvsr69/nvsr69-12-508.pdf` (2018), `nvsr70/nvsr70-19.pdf` (2019), `nvsr71/nvsr71-01.pdf` (2020), `nvsr72/nvsr72-12.pdf` (2021), `nvsr74/nvsr74-02.pdf` (2022), `nvsr74/nvsr74-06.pdf` (2023), `nvsr75/nvsr75-05.pdf` (2024) | Paths from the NVSR listing; 2010, 2017, 2018, 2019, 2022, 2023 and 2024 downloaded and their table lists read |
| *Deaths: Final Data*, 2018–2022 | Under the same root: `nvsr69/nvsr69-13-508.pdf` and `nvsr69/nvsr69-13-tables-508.pdf` (2018); `nvsr70/nvsr70-08-508.pdf` and `nvsr70/nvsr70-08-tables-508.pdf` (2019); `nvsr72/nvsr72-10.pdf` and `nvsr72/nvsr72-10-tables.pdf` (2020); `nvsr73/nvsr73-08.pdf` (2021); `nvsr74/nvsr74-04.pdf` (2022) | All downloaded |
| *Deaths: Final Data*, 2010–2017 (E-S1) | `nvsr61/nvsr61_04.pdf`, `nvsr63/nvsr63_03.pdf`, `nvsr63/nvsr63_09.pdf`, `nvsr64/nvsr64_02.pdf`, `nvsr65/nvsr65_04.pdf`, `nvsr66/nvsr66_06.pdf`, `nvsr67/nvsr67_05.pdf`, `nvsr68/nvsr68_09-508.pdf`, and the internet-table files each report's list of internet tables names | Reports downloaded; internet-table files not located |
| Public LMF, NHIS 2009–2018 | https://ftp.cdc.gov/pub/Health_Statistics/NCHS/datalinkage/linked_mortality/NHIS_2009_MORT_2019_PUBLIC.dat through `NHIS_2018_MORT_2019_PUBLIC.dat`, and `R_ReadInProgramAllSurveys.R` in the same folder | Names, sizes and dates from the folder listing; no file downloaded |
| NHIS 2009–2018 data files | https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Datasets/NHIS/ followed by the year | Not listed in this job; the fit job lists each year's folder and records the sample-adult and person file names, sizes and hashes |
| NHIS 2009–2018 documentation | https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Dataset_Documentation/NHIS/ followed by the year, files `samadult_layout.pdf`, `personsx_layout.pdf`, `srvydesc.pdf` | 2009, 2016 and 2018 downloaded |
| ACS 1-year PUMS person files, 2010–2024 | The Census Bureau's PUMS directory, https://www2.census.gov/programs-surveys/acs/data/pums/ followed by `<year>/1-Year/`; for 2020, the file with experimental weights under https://www2.census.gov/programs-surveys/acs/experimental/2020/data/pums/1-Year/, which the Census Bureau's 2020 experimental-PUMS page links | **Not checked**: no round fetched or listed a data directory. The fit job confirms each URL and records sizes and hashes before use |
| ACS PUMS documentation, 2010–2024 | Data dictionaries under https://www2.census.gov/programs-surveys/acs/tech_docs/pums/data_dict/ (`PUMSDataDict10.pdf` to `PUMSDataDict12.pdf`, `PUMSDataDict13.txt` to `PUMSDataDict16.txt`, then `PUMS_Data_Dictionary_<year>.txt`); subject definitions under https://www2.census.gov/programs-surveys/acs/tech_docs/subject_definitions/ (`<year>_ACSSubjectDefinitions.pdf`); top-coded values under https://www2.census.gov/programs-surveys/acs/tech_docs/pums/top_coded_values/. The 2020 1-year dictionary sits only under https://www2.census.gov/programs-surveys/acs/experimental/2020/documentation/pums/ (`PUMS_Data_Dictionary_2020.txt`) | Fix round 1 fetched every dictionary but 2020's, every subject-definitions file 2010–2024 and the 2024 top-coded values (§13.6). 2020's dictionary lay outside that round's cleared path; fix round 2 reads the lane's fetched copy and closes its code-list item (§8.2, §13.7) |
| ACS 2020 experimental documentation: `PUMS_Data_Dictionary_2020.txt` | https://www2.census.gov/programs-surveys/acs/experimental/2020/documentation/pums/PUMS_Data_Dictionary_2020.txt | Lane-fetched copy; fix round 2 checked SHA-256 `eab88ac77bc2df8273409a85b841c9ea18879982f575eb15cedf6ee3c965e6e3`; §13.7 |
| ACS 2020 experimental documentation: `ACS2020_PUMS_Variable_Changes_and_Explanations.pdf` | https://www2.census.gov/programs-surveys/acs/experimental/2020/documentation/pums/ACS2020_PUMS_Variable_Changes_and_Explanations.pdf | Lane-fetched copy; fix round 2 checked SHA-256 `698c4cb6dc09bb0191c12352b710939585e86d8993683cbcac49e1118f3acd24`; §13.7 |
| ACS 2020 experimental documentation: `ACS2020_PUMS_Variable_Changes_and_Explanations.pdf.txt` | https://www2.census.gov/programs-surveys/acs/experimental/2020/documentation/pums/ACS2020_PUMS_Variable_Changes_and_Explanations.pdf | Lane-fetched copy; fix round 2 checked SHA-256 `a4d94973c3d4416b6e1dd9a871541b953377a99f3ef006b689a94213de24b9a4`; §13.7 |
| TR 2026 death probabilities | Already in the repository behind `data/tr2026.death_probability` (S0.1 §1.1) | — |

### 11.7 Invariants for property-based tests (Hypothesis, invented data)

- Printing intervals contain the printed point, widen as the half-width
  grows, and swapping the two values negates the interval.
- On generated finite `0 ≤ m < 2` and finite `μ ≥ 0` whose floating-point
  conversion stays below one, `q = m / (1 + m/2)` and
  `q = 1 − exp(−μ)` increase, stay in `[0, 1)` and invert within numerical
  tolerance. Values `m ≥ 2` lie outside this property's domain.
- Every completed table holds each category, sex and age 0–120 exactly
  once, with zero reference coefficients, and §5's rules reproduce the held
  values exactly.
- **Calibration round trip:** invented coefficients and an invented
  reference population that passes the support/rank checks generate
  targets, and §6.3 recovers the
  coefficients within `1 × 10⁻⁹`. With `λ = 0` and one dimension varying,
  JR-C equals JR-A on identifiable fixtures only. The null-direction
  fixture with perfectly coincident education/race membership and
  coefficient shifts `(b, −b)` must fail the design/Jacobian rank check,
  even when both starts coincide and all categories have support.
  Permuting rows, or scaling every weight by one
  constant, changes no coefficient.
- Each calibrated table passes `RelativeRiskSpec` and SM1's cell
  conservation on the invented population.
- `Q̃`'s quintiles hold exactly one fifth of the weight at every sex and
  single age, ties included; permuting records, inside a tie block or
  across the file, changes no membership; and the ordered logit, fitted to
  invented records whose quintile weights equal the model's expected
  shares under known `λ` and cut points, recovers them within
  `1 × 10⁻⁶`, converging under §6.2's rule from §6.2's start.
- When the invented population's attributes are independent, its
  quintiles hold one fifth each, nothing caps, and the invented source
  tables come from the same coefficients on the same population, the
  fitted and target e65 agree exactly for every earnings quintile. For a
  race and Hispanic-origin group they then differ by the tail alone:
  `e65_F,g − e65_T,g = l(100) / l(65) × (e100_F,g − e100_T,g)`, with
  `e100_F,g = life_expectancy(q_F,g[0..120], 100)`, because NCHS's
  equation 17 and `life_table.py`'s `Lx = lx − 0.5 dx` give the same
  person-years at 65–99 (`life_table.py:13`; NVSR 75(5) p. 61). The two
  agree exactly when the invented open-interval ratio `e100_g /
  e100_total` also equals `e100_F,g / e100_base`. The fitted life tables
  satisfy `life_table.py`'s invariants.
- **NCHS-closing identity (M7):** with every invented NCHS ratio equal
  to one (`ρ_g(a) = 1` at 65–99 and `e100_g = e100_total`), §9.2's race
  target equals `life_expectancy(q_base(s, ·, t)[0..120], 65)` within
  `1 × 10⁻¹²`.
- **NHIS implied value under proportional hazards (M-H1):** when every
  category's hazard at each age of a band equals a fixed multiple of the
  reference category's, the age-standardized implied value of §4 equals
  the log of that multiple for any positive weights `W` and any age mixes
  of the two categories. A companion example with invented values shows
  the crude ratio failing the same check when the age mixes differ.
- **Endpoint checks (r2 M1):** use separate Cornish–Fisher endpoints for
  invented skewness −1.2, −1.5 and +1.2; reject all three under §9.3's
  validity guard, never accept a negative half-width, and test valid
  small positive/negative skewness, ordering, each endpoint's jackknife
  error and doubling/exhaustion outcome.
- **Age-mix counterexample (r2 M2):** equal category hazards at two true
  ages with unequal category age mixes must give zero category log ratio
  from the single-age Poisson fit and from §4's implied value, within
  numerical error. When the public age pools those ages, option (b) in
  §4.5 leaves the affected required members unidentified/inconclusive;
  no coarse-stratum estimate can pass them.
- **Other-group target (r2 M3/M10):** carry an invented extraction with
  printed `qx`, open `lx` and `Tx`, rounding widths and provenance
  through constant-force conversion with a non-unit HR, source-total
  division, baseline rescaling, cap, M-R7 and the whole e65 target.
  Compare the direct sum with a separately seeded backward recursion;
  never multiply source `qx` directly by HR. Reject incompatible radix
  or open-interval provenance and missing `lx`/`Tx`.
- **Joint dependencies (r2 M4):** in an invented one-age joint
  earnings/race population hold the race hazard target fixed and vary
  earnings; race marginal probabilities must change. In the review's
  two-age fixture hold the earnings band target fixed and vary race;
  earnings single-age probabilities must change. Both changes enter
  e65 residuals; absent an invariance proof each derived member needs
  both components under §9.3. Same-target successful-refit contrasts
  still cancel for NHIS and OACT alike.
- **Same-quarter deaths (r2 M5):** every invented valid interview/death
  quarter, including equal quarters, has positive event exposure and a
  finite Poisson log offset under M-H2 and H-TIME. Invalid chronology
  stops rather than drops records or repairs dates.
- **Nesting/singletons (r2 M9):** repeated household/family numbers in
  different survey years never collide; a true within-year family
  spanning PSUs fails nesting. A full-sample singleton must stop variance
  estimation and cannot yield a passing zero variance.
- The digitizer recovers known values from synthetic vector figures
  within the plotting tolerance and rejects a figure with inconsistent
  ticks.
- The NHIS estimator recovers known hazard ratios from synthetic
  person-time; the bootstrap never moves a PSU across strata.
- The suppression writer refuses any artifact with a cell under 100
  persons or 20 deaths.
- `WideningCoefficientPath` equals P-PRIMARY through 2024, its multiplier
  lies in `[1, 1.5]` and stops changing after 2054, and race coefficients
  never move.

### 11.8 Differential tests

- The two table transcriptions (A4), and Tables 1–6 against Tables 7–12
  (A2).
- Newton's solution against a generic root finder on the same equations,
  on invented inputs.
- The fit's normalization against SM1's `normalize_probabilities` called
  directly on the expanded rows.
- `period_life_table` against `life_expectancy` for every fitted table,
  both with `f0 = 0.5` (§9.6).
- §9.2's direct sum for a race and Hispanic-origin target,
  `(Σ_{a=65..99} L(a) + l(100) × e100_T,g) / l(65)`, against
  `life_expectancy` on ages 0–100 with the probability at 100 set to
  `1 / (e100_T,g + 1/2)`. The constant-terminal-`q` closing gives
  `e_w = (1 − q_w / 2) / q_w = 1 / q_w − 1/2` at the last age
  (`life_table.py:25`, 170), so the recursion starts from `e100_T,g`; the
  test draws `e100_T,g ≥ 1/2`, which keeps that probability in `(0, 1]`.
- The NHIS Poisson estimator against a direct person-year rate ratio on
  synthetic data with one covariate.
- The replicate-variance code against a hand formula on synthetic
  replicates.

## 12. Rules for two boundary cases

Choices inside SM2 are this record's, and it states them. Two cases
reach past those choices, and the lane's coordinator ruled on both for
this record.

1. **A failed figure digitization stops SM2; the table-only path doesn't
   stand in for Q6's primary.** If the digitization fails its validation,
   SM2 stops and reports, the fit publishes P-TABLE as a labeled
   sensitivity, and the question goes to Max with the failure's evidence,
   because using the 2020 tables as the last observed level amends Q6.
   Nothing waits on this now; SM2's admission waits only if the validation
   fails.
2. **SM2's primary never takes its reference covariates from the
   population of the held-out gate that tests it.** This applies the
   existing held-out separation and sets no new principle. SM2 stays on
   public data, so SM3 tests a model fitted without its own population; a
   reference population built from SM3's population (JR-F) could run only
   inside SM3's authorized step, as a registered sensitivity. PSID use
   follows the project's data-access record. If a later
   calibrate-then-test pair wants a different answer, that call spans
   gates and goes to Max then. Only JR-F depends on this rule; nothing in
   the primary path does.

This record amends none of Q4, Q5, Q6 or Q11.

## 13. Files read

### 13.1 Restricted lists

The job's stream records the parts below. It requested a maximum of 60
lines but read one 61-line part: entry c, lines 61–121. This corrects the
earlier blanket claim of at most 60. Its report says each part showed in
full and it opened no harness-saved copy; the command-only trace cannot
independently establish display completeness (§13.7).

| File | SHA-256 | Parts |
|---|---|---|
| `EV/RESTRICTED-FILES.md` | `b09a2a56533b6880dd832135a60d315e171fa6850079940d8c1aee795f1a6351` | 13 (lines 1–742) |
| `EV/coordinator/restricted-files-pending-20261024.md` | `4b4936f05955541d4ad8b09ecf35ff01d73df104b01ae06c3446122e815ab931` | 2 (1–105) |
| `EV/coordinator/restricted-files-pending-20261025.md` | `9f78e02177b3591c58f7177179fdcb018d4daedf64b909e6dd6824e03e5972ac` | 1 (1–23) |
| `EV/coordinator/restricted-files-pending-20261025b.md` | `0fb8ba87bd8098062b3a133a2e501c0394ac34716e8ee93f1fb749baabf35a69` | 1 (1–38) |
| `EV/coordinator/restricted-files-pending-20261025c.md` | `8268e05c8f2e885aa114eb08391db13dc13ea78be503a582b015fda88738774b` | 2 (1–60; 61–121, the latter 61 lines) |
| `EV/coordinator/restricted-files-pending-20261029.md` | `c405c38194a3a3535b275d84e458964b9f71ce50fd058339ac57c8c54e025609` | 1 (1–26) |

`EV` is `/Users/maxghenis/microcosm-launch-evidence/dynasim-parity-20260909`.
No other pending file existed, and all six hashes matched the brief.

### 13.2 Repository files, at `18082859`

| File | SHA-256 | What the job read |
|---|---|---|
| `docs/design/mortality_groups_financing.md` | `5ee8d4f5df12c1777503984def7717fbfe8285cb0cf038a15eb9e3fe40051cfe` | Lines 1–152, 304–411 and 467–1022, and its headings |
| `docs/design/s0_1_source_audit.md` | `486d63c91f95e49b97a1012fb41fe5a6937c94194400bf0e5778bd3835f668fc` | Lines 1–200, 324–707, and its headings |
| `docs/design/s0_1_power_results.json` | `58569c9667c1c1af0e5d5a2fcc0d0e4cd1ed8002fb44d5fe01370f60f1ac74f3` | Top-level keys only |
| `docs/design/mortality_ses_sm1.md` | `0000b20134b17df1b522795e742a5557ff8c909b89bfdc955e5ec544315c4990` | Lines 1–100, 273–332 |
| `scripts/s0_1_power.py` | `c891a1f8391edb593f0d86f6ac9c333e053854347179da5dbafc301b0000679e` | Two lines found by a search for SM2 terms |
| `src/populace_dynamics/mortality_ses/__init__.py` | `5dfb1958b60144f71a7bb54d8a11848bd37670fb2d82fca873650dcf6bc53dd1` | In full |
| `src/populace_dynamics/mortality_ses/model.py` | `32dfd76dcd8ef6fe237123c043657289178ca150f4ceede76a92afc3ed9e4cdd` | In full |
| `src/populace_dynamics/mortality_ses/normalizer.py` | `44e5331a83b63d9a7e5c180af04a3fc4c173da08b90ae8c7d8a88958fe869015` | Lines 1–140 and `normalize_probabilities`'s docstring |
| `src/populace_dynamics/mortality_ses/specification.py` | `6a698b2a134d106becc2b34b2c5ea9b050b804d202c870333265ddb15503f84f` | In full |
| `src/populace_dynamics/mortality_ses/step.py` | `08be41603343908df4d6a8d6122aedc4fcdc02fc29865f5c9da9786df24b900d` | In full |
| `tests/mortality_ses/test_model_step.py` | `259ff37cf36b3fdfebd181fbf448beddd19461f0e5c54825870e4643f2b641b2` | Line count and hash only |
| `tests/mortality_ses/test_normalizer.py` | `84a4a48710856c5a600c9b50da73be104af8d52f0abb84de14f70e53f2074f25` | Line count and hash only |
| `tests/mortality_ses/test_properties.py` | `99e881749a3e65ace684038ebdc23d6f8d8fbfb19e76e5b64f467d88d96ad8ee` | Line count and hash only |
| `tests/mortality_ses/test_specification.py` | `2e736ee32e3dc79ba171b2e41b9d185ef5fac943717853ab04e66b6e1357738a` | Line count and hash only |
| `src/populace_dynamics/data/life_table.py` | `ab9f23bd155734b219c36f2cade0d1eb926e364ef39b0b91179b9e5ccd5dff92` | In full |
| `src/populace_dynamics/baselines/base.py` | `52e80c94c0206adcba0b0ff6e78ff1af5d9e12f49d33c76d14051caf29de6fd6` | Lines 1–60, 140–315 |
| `src/populace_dynamics/engine/di_entitlement_rates.py` | `6000ba7b7039e2359920d62fd7f4c4948d729917a39ef7ad8c28d9f3da3c9ba3` | Lines 1–80, 105–120, 180–215, and a search for its mortality fields |
| `src/populace_dynamics/estimates/group_breakdown.py` | `8b1821c264be68a00e8f867fb09790ecf52dd6658a129343f4f93171ec939f72` | Lines 1103–1130 and 1227–1274, by one `sed` command. Departure: the hash command also read the whole file's bytes; the job displayed and searched nothing else in it. The hash equals the one S0.1 records at `2195258c` |

Also departing from the brief's list: the same hash command read the
repository's `CLAUDE.md`
(`594161147040726b7b36d75814e0336b5fcf601db4b5a23e1a95972005aa78e3`),
whose text the harness had
already placed in this job's context; and the job read
`.git/info/exclude` to confirm that git ignores `.sm2-scratch/`.

### 13.3 S0.1's source folder

`S` is `EV/mortality-groups-financing-20261021/s0_1-sources`. The job opened
every file below by exact name; each hash matches `S/files.sha256`.

| File | SHA-256 | How read |
|---|---|---|
| `MANIFEST.md` | `37b1dbf9c8fe520787dbc69a4accf917b33372b832ab518e94b3dc07515e6892` | In full |
| `files.sha256` | `a5e5b6171009c62afe4549bcab8c6900cd52af865b041cd160fae1a060d20ed0` | Lines for the files below |
| `oact_study129.pdf` | `937ec3b6c3109426ba8d87e0956e320bdc29ab6ffa07625ae1b379635d04e414` | Page 27's top lines; image list and content-stream operator counts for pp. 33–38 |
| `oact_study129.txt` | `c94bebb0f918396f04c990c7f1d495d982f9d7a8503e0db637bd30ee3ac21f90` | Text pp. 1–14 with decimals masked; table and figure layouts masked |
| `oact_study124.pdf` | `ef66df96b8a21fe59bf4fef79aa48c950d3fff866e6725f4dd5c5f339f10ac38` | Not opened (its text file was) |
| `oact_study124.txt` | `c8716f9346c6ddacd2f1ee5e35f0657cc5ca28ffe6f51446cb434ce5707aa385` | Text pp. 2–10 masked; table layouts masked |
| `oact_tbosley_20250114.pdf` | `33a192b5725ef338060044533b7f9c3389dde762ddefdcaa26677bc25d468d46` | First lines of slides 1–4 and 20–23 |
| `nchs_nvsr74-02.pdf` | `3312964360b9a33663be89248f7e75c39e99f895dd04ca86659115fe1a318421` | Not opened |
| `nchs_nvsr74-02.txt` | `ccab51d670a1290a69dc07caa8e2dd7138fad6eefca2074bc23089d5063b2707` | Table titles and pages; decimal counts of one table |
| `nchs_nvsr75-05.pdf` | `43e24a1f249f017fcc505a601eb5738f0797506e35b67c4722c91791777d8842` | Not opened |
| `nchs_nvsr75-05.txt` | `59a05b2078ca221dd3e04c6490396b9a8b91e24af1f4d8de4868730975797615` | pp. 1–4 masked; table titles; technical notes pp. 53–55 masked |
| `nchs_nvsr74-04_deaths_final_2022.pdf` | `bb7b356841b202cba6a845315679b42424945a78240414dbe67bd100d428b26b` | Not opened |
| `nchs_nvsr74-04.txt` | `ec24a46d03bb361e5038659a56c5340ba5d330151d3cc02f2a49b1674bcff1db` | Table 14 (p. 86) and Table VIII (p. 133) masked; technical notes pp. 127, 132–133 masked |
| `nchs_lmf_public-use-linked-mortality-file-description.pdf` | `2e9cae2ffd17b276d200f9388860e682f995a7210bb004bdba54f63f412e446c` | Not opened |
| `nchs_lmf_public-use-linked-mortality-file-description.txt` | `f426c84347536f8635fddfef9a72950693cd22ae9fced81cddcc155b11775331` | In full |
| `nchs_lmf_public-use-linked-mortality-files-data-dictionary.pdf` | `5a62ebb5573030ce448756fc48f0618561d713aa4b48b9b1a2669ff20db7bbd6` | Not opened |
| `nchs_lmf_public-use-linked-mortality-files-data-dictionary.txt` | `5cdb8645bc99cc224654d11cf993ee23758ac51f0c857757df1483616c9098b5` | In full |
| `nchs_lmf_public.html` | `0d599231ec9d3450066a9d9537b9a83272746b87336c73e6ea45ca2e8aeb55c3` | Text lines on files and dates |
| `nhis2018_personsx_layout.pdf` | `186bb42ff139503b2a2263f227ca558dd82fab99a77c25395af66ae0fc366322` | p. 294 |
| `nhis2018_samadult_layout.pdf` | `9ab1b5345df69c11cff74ee1921abb2d02d3b7e698061c0d08589d00012da9a0` | pp. 6–11 |
| `nhis2018_srvydesc.pdf` | `62662706d190edd80f7225a4f228169566defe5bf6f3a2a6ae29d3f17c4c1246` | pp. 25–26, 70–72 |
| `cbo_wp2007-11_cristia.pdf` | `e8f376a6330b320bf778ac50a8831b21fbb7884a9f9b72bea761d720f779524c` | Not opened |
| `cbo_wp2007-11_cristia.txt` | `199af4eab22c9313bb7cc4e1b4981de7357b93b66b3e3d07a75675e8b7247c46` | Printed pp. 6–12, 14, 18–19 masked; Tables 1, 3, 5, 6 and Figure 2 layouts masked. This list left out Table 4, on which M-C4 relies; fix round 1 read its layout with every number masked and confirmed its race block (§13.6) |
| `cbo_41681.pdf` | `e22720ad1ca203c5a801e61094c17a01d050b0c57ce929fa7dcb1d09573fb467` | Not opened |
| `cbo_41681.txt` | `f6d2891687ecb41ac06201e2c0fbd856fe126d0c4ce9376c257875a2cdc973af` | pp. 1–3, lines matching definitions and sources, masked |

"Masked" means a filter replaced decimals and comma-grouped counts before
display. Some integers still showed: page and year labels, a few
three-digit counts in Table 14's "not stated" row, and one three-digit
AIME breakpoint in Study 124's Table 2. None of them appears in this
record. The first job's report names two more leaks that this paragraph
left out: the percentage shares in Study 124's Table 3 and the
percentages in Study 129's text, and the TR 2026 example values in
`life_table.py`'s docstring. None of those appears in this record
either.

### 13.4 Documents this job fetched

Thirty-three files from `www.cdc.gov/nchs/` and
`ftp.cdc.gov/pub/Health_Statistics/NCHS/`, with URLs, retrieval date
(1 November 2026), sizes and SHA-256 in `.sm2-scratch/sources/MANIFEST.md`,
which the lane moves out of the clone after the job:

- the NVSR index page, its script and its listing CSV, and the NCHS
  life-table index page;
- *Deaths: Final Data* for 2010–2021, and the internet tables for
  2018–2020;
- *United States Life Tables* for 2010, 2017, 2018, 2019 and 2023;
- the public linked-mortality FTP folder listing;
- the NHIS 2009 and 2016 documentation folder listings, sample-adult and
  person layouts and survey descriptions.

None is microdata. The job opened no ssa.gov, census.gov or other host.

### 13.5 Files not opened

Three times a slow command ran past its time limit and the harness moved
it to the background, saving its output under
`/private/tmp/claude-501/-Users-maxghenis-PolicyEngine--mgf-sm2/…/tasks/`
(a page-mapping loop over Study 129, a fetch-and-convert loop over the
NHIS layouts, and a search with a Python check); a fourth time a commit
and push did. The job stopped the first three and opened none of the four
saved files.

### 13.6 Fix round 1 (3 November 2026)

A second job revised this record to answer independent review r1
(`EV/mortality-groups-financing-20261021/builds/sm2-review-r1.md`). It
counts as exposed, like the first, and nothing from it feeds a blind role.

**Restricted lists.** It read the six lists of §13.1 and a seventh,
`EV/coordinator/restricted-files-pending-20261101.md`
(`84ab3e1f4c5824a3fd97f8a742a293737deabc680d674724e7e6f2cf4dfc00f5`, 16
lines). The round reported parts of at most 30 lines, every part shown
in full, and no harness-saved copy opened. Its path-only `reads.md`
confirms the seven paths, but records no part boundaries or sizes; fix
round 2 cannot independently verify that size/display claim from it.
All seven hashes matched its brief, and no
newer pending file existed.

**Documents fetched.** Thirty-five files on 3 November 2026, from
`www.census.gov/` and `www2.census.gov/programs-surveys/acs/tech_docs/`
only; none is microdata. `DD` is
`https://www2.census.gov/programs-surveys/acs/tech_docs/pums/data_dict/`
and `SD` is
`https://www2.census.gov/programs-surveys/acs/tech_docs/subject_definitions/`.

| What | URL | Bytes | SHA-256 |
|---|---|---:|---|
| Data-dictionary directory listing | `DD` | 35542 | `6353cd1d26a14086aa6ed2f3edc5fcc1b09e60546de0e19910d00409b5944579` |
| 2010 data dictionary | `DD` `PUMSDataDict10.pdf` | 369558 | `4b4cc0b1adca2abff28e67cf796b6074e45cdf9c8609b88c5e4a45d84fb8fb48` |
| 2011 data dictionary | `DD` `PUMSDataDict11.pdf` | 360302 | `a0127a8b40d472a11def2efc6dc3a88b8425b707a6eb63f860002c641c054963` |
| 2012 data dictionary | `DD` `PUMSDataDict12.pdf` | 369966 | `89570a1831bc5c9ee5a72cd89ebdda978ef1f799f1d1353e418f3e1eeb409b1b` |
| 2013 data dictionary | `DD` `PUMSDataDict13.txt` | 264904 | `14f0061974fc6a1db746679766abe1c4d81afd8e4ef4b5b83579e64d136f98c2` |
| 2014 data dictionary | `DD` `PUMSDataDict14.txt` | 190795 | `9dd3f70392159c4fa15b55b437ea77796f877b3ec8973561c9762b697abb1f7c` |
| 2015 data dictionary | `DD` `PUMSDataDict15.txt` | 207251 | `0b6b75d176dcb8572972d11d303ff1f02a11d1b58ca40702508ab3b834dade53` |
| 2016 data dictionary | `DD` `PUMSDataDict16.txt` | 211482 | `b21a4dd6500b03fe61de92f5433a3b25b635b07492a9806b51db2d8a49e2b89b` |
| 2017 data dictionary | `DD` `PUMS_Data_Dictionary_2017.txt` | 294848 | `ea5bcde2a07b0c76ac145fac108e9013480b686a9d70afc4e3f4a6512ccbfd69` |
| 2018 data dictionary | `DD` `PUMS_Data_Dictionary_2018.txt` | 298670 | `843a18e15b6cb7c7326261d478947a1415c4674c62419a8d01946a5a5df4d5fd` |
| 2019 data dictionary | `DD` `PUMS_Data_Dictionary_2019.txt` | 300134 | `2ecbd86e979aa4e94945012e7537e53c37a4deff7f0435adb000b98b5a50ce77` |
| 2021 data dictionary | `DD` `PUMS_Data_Dictionary_2021.txt` | 301277 | `53fb9da5c36b68670c54ab12baa13c4767f6b3e43db326585635c5a333090b60` |
| 2022 data dictionary | `DD` `PUMS_Data_Dictionary_2022.txt` | 301115 | `4a920e7c2a83dc5bede6620e5edf9bed825a8950072271bbbadd800c400ba9e6` |
| 2023 data dictionary | `DD` `PUMS_Data_Dictionary_2023.txt` | 303015 | `0e58d8edd725d44035c32ee2697acb3963eb39c36caf4096e0ce494c64bb6dc6` |
| 2024 data dictionary | `DD` `PUMS_Data_Dictionary_2024.txt` | 306867 | `9a98282277aa7f2dafb12b0bdf38b258689d3a1a9c2abbd9b5e2c1ddde6f7b32` |
| Subject-definitions directory listing | `SD` | 20306 | `a2e01395460524851da9ce5eee71732f61667e56cbf914cc65d6ecbd17117a82` |
| 2010 subject definitions | `SD` `2010_ACSSubjectDefinitions.pdf` | 688859 | `dd016f630ab0435e2e3edfe21ec5aed5ca5a24391e1efb7a5f022d0332336012` |
| 2011 subject definitions | `SD` `2011_ACSSubjectDefinitions.pdf` | 700744 | `7eedd173f80fccf700edf83628b4c0d6ae14b1bcc8b7a41f2c5d59a28366cd5e` |
| 2012 subject definitions | `SD` `2012_ACSSubjectDefinitions.pdf` | 804765 | `61c7199b24f9ac03b46bfaef968ea152e9d4ab427d43772f05cfc48b842da62f` |
| 2013 subject definitions | `SD` `2013_ACSSubjectDefinitions.pdf` | 813312 | `bcc860028009411b4b45961a7abc50ecc4eaf2cea3e7676da8bbc8fcc3a98d9f` |
| 2014 subject definitions | `SD` `2014_ACSSubjectDefinitions.pdf` | 1216961 | `bff06e9d1477147c5171aacb452954a554f21d465bbe4e96322dd03c7ca7a048` |
| 2015 subject definitions | `SD` `2015_ACSSubjectDefinitions.pdf` | 851793 | `881329f214c54e4249165c271107d599b906a96561e9415739ad08f487ffef7d` |
| 2016 subject definitions | `SD` `2016_ACSSubjectDefinitions.pdf` | 1422620 | `028829c7dc01d5575bd9ecb4bf373f559ad1590be7599ce2de448d66a583203f` |
| 2017 subject definitions | `SD` `2017_ACSSubjectDefinitions.pdf` | 932466 | `8676e64c48a8519da8648764ad7b326603f12fa1c8a9e0fba9b6965a03e85112` |
| 2018 subject definitions | `SD` `2018_ACSSubjectDefinitions.pdf` | 1653091 | `842c8188751a22208a71360c8474c770236c313e58196356cb998bb0724f260c` |
| 2019 subject definitions | `SD` `2019_ACSSubjectDefinitions.pdf` | 1076378 | `ce42270355d9dce11fe8608454402fb80b9b0ce4a4e83ebd55a71f8a117574ed` |
| 2020 subject definitions | `SD` `2020_ACSSubjectDefinitions.pdf` | 1091755 | `70082ff6739486fa9e7524c34507f59a292d05afcb5fc9f3402a7985ecde5bc5` |
| 2021 subject definitions | `SD` `2021_ACSSubjectDefinitions.pdf` | 1088859 | `a1db9fb258ff6ff25c5ac4d9a4817eca35f31bb49e238aaad616e6d6f568398e` |
| 2022 subject definitions | `SD` `2022_ACSSubjectDefinitions.pdf` | 1136140 | `3ba434d7c72ae71c6c8fe4903493cc063a92eca488b89e2e1e490124378caeed` |
| 2023 subject definitions | `SD` `2023_ACSSubjectDefinitions.pdf` | 1102515 | `6edcfa27b10eaea093867256523cdc6f256a6c7991f4b02823d9034de2e31033` |
| 2024 subject definitions | `SD` `2024_ACSSubjectDefinitions.pdf` | 1170567 | `6e0c5b1a5d3ebf7e300e583ac6424cbd5f09de50d69e7ef03aa6d070d9c4a7a8` |
| 2016–2020 PUMS documentation page | https://www.census.gov/programs-surveys/acs/microdata/documentation.2020.html | 368498 | `0893dd7309bb7f88026e3ae23ca8011f127178a8c281c85b6a99a0a6f0bf59c8` |
| 2020 experimental-PUMS page | https://www.census.gov/programs-surveys/acs/data/experimental-data/2020-1-year-pums.html | 351006 | `3fc562a7536230843d11fc04dd01b491b73772b0fdb99726f0feb1955212e7b1` |
| 2024 PUMS documentation page | https://www.census.gov/programs-surveys/acs/microdata/documentation.2024.html | 380383 | `b84b42278085eeb4731df9442200a02f207f9f1dd14123b30ee202c54b5fea05` |
| 2024 top-coded values | https://www2.census.gov/programs-surveys/acs/tech_docs/pums/top_coded_values/2024PUMS_top_coded_values.pdf | 155706 | `d5ff127b7cfa33a8bbea84590472a0ae5806054762ac246471648f38b56196a7` |

From the dictionaries the round read the entries for `SSP`, `SCHL`,
`HISP`, `RAC1P`, `AGEP`, `ADJINC` and `SEX`; from the subject definitions,
the Social Security income definition; from the top-coded-values
document, its variable list and its explanation of top-coding; from the
pages, their links and the 2020 page's note on experimental weights. The
2020 1-year dictionary sits under
`www2.census.gov/programs-surveys/acs/experimental/`, outside the round's
cleared path, so it fetched nothing there.

**Other files opened outside the repository.** The review r1 file; from
the review's scratch folder, `m1_invented.py` and `schema_check.py`; the
first job's brief, report and OACT counts check; in S0.1's source folder,
`files.sha256` (the lines for the files below), `oact_study129.txt`
(lines on pp. 2–9, masked), `nchs_nvsr75-05.txt` (pp. 1–2, the table
notes and technical notes pp. 53–62, masked), `nchs_nvsr75-05.pdf`
(the text of pp. 57 and 59, masked),
`nchs_nvsr74-02.txt` (a search for classification ratios),
`nchs_nvsr74-04.txt` (p. 132, masked),
`nchs_lmf_public-use-linked-mortality-file-description.txt` (p. 1),
`nchs_lmf_public-use-linked-mortality-files-data-dictionary.txt` (a
search for a perturbation flag), `nhis2018_samadult_layout.pdf` (pp. 6–8),
`nhis2018_personsx_layout.pdf` (p. 294, the `EDUC1` codes),
`nhis2018_srvydesc.pdf` (converted to text in the round's scratch folder;
search hits on pp. 8, 16, 70 and 82–94, and pp. 83, 92 and 93 read),
`cbo_41681.txt` (pp. 1–2, masked),
`cbo_wp2007-11_cristia.txt` (table titles, and Table 2's layout with
every digit masked) and
`cbo_wp2007-11_cristia.pdf` (Tables 1, 2 and 4, PDF pp. 36, 37 and 39,
every number masked); in the SM2 source folder, `files.sha256`,
`nchs_us_life_tables_2019_nvsr70-19.txt` and
`nchs_us_life_tables_2023_nvsr74-06.txt` (searches for classification
ratios). Each hash matched its folder's `files.sha256`.

**Repository files.** This record; `docs/design/s0_1_source_audit.md`
(lines 1–60 and 324–707); `docs/design/mortality_groups_financing.md`
(the lines this record cites, and a search for its mentions of the
closing rule, which found lines 143 and 1146); `src/populace_dynamics/data/life_table.py`
(in full); `src/populace_dynamics/mortality_ses/specification.py` (a
search for the columns it reads, lines 203–224); and `pyproject.toml`
(lines 118–130, the pytest settings, read before the test run below, a
file outside the brief's read list).

**What showed despite masking.** A few one- and two-digit counts from
Table I of NVSR 70(19) and 74(6); number words and one axis label in CBO
41681's prose on pp. 1–2; in the ACS dictionaries, the `ADJINC` factors
and the dollar bounds of the income items; and the TR 2026 example values
in `life_table.py`'s docstring, which the round read in full; and one
count in NVSR 75(5)'s prose on p. 2, which a search for the life-table
column headers displayed. None of them appears in this record.

**Code the round ran.** Edit scripts on this file, and one check in its
scratch folder that ran `life_table.py` on invented life tables to test
§9.2's formulas (the direct sum against the seeded recursion, the
identity with every ratio at one, and the tail term of §11.7). It ran
nothing on real data and computed no outcome. It also ran
`tests/mortality_ses` serially with `-p no:cacheprovider`: 116 passed.
Those tests import repository modules beyond SM1's, though not
`estimates/group_breakdown.py`, and the run displayed none of their
content.

### 13.7 Fix round 2 (7 November 2026)

Codex (GPT-6) revised only this repository file for review r2. The job
counts as exposed, opens no microdata, computes no real-data outcome,
fetches nothing, and feeds no blind role. It leaves the working tree
uncommitted because this lane's sandbox cannot write `.git`; the lane
handles the commit and PR update. Scratch and the proposed PR body stay
in `.sm2-fix2-scratch/`, outside the repository's tracked file set.

**Restricted lists.** The job first read all eleven lists with visible
`sed -n 'a,bp'` parts of at most 60 lines; it opened no saved output.
Every hash matched the brief; no newer pending file existed. It applied
all ten pending files, and none closed a permitted input.

| File | SHA-256 | This round's parts |
|---|---|---|
| `EV/RESTRICTED-FILES.md` | `b09a2a56533b6880dd832135a60d315e171fa6850079940d8c1aee795f1a6351` | 15 nonempty parts (40 or 60 lines requested), plus one empty EOF read |
| `EV/coordinator/restricted-files-pending-20261024.md` | `4b4936f05955541d4ad8b09ecf35ff01d73df104b01ae06c3446122e815ab931` | 2 parts (1–60, 61–120) |
| `EV/coordinator/restricted-files-pending-20261025.md` | `9f78e02177b3591c58f7177179fdcb018d4daedf64b909e6dd6824e03e5972ac` | 1 part (1–60) |
| `EV/coordinator/restricted-files-pending-20261025b.md` | `0fb8ba87bd8098062b3a133a2e501c0394ac34716e8ee93f1fb749baabf35a69` | 1 part (1–60) |
| `EV/coordinator/restricted-files-pending-20261025c.md` | `8268e05c8f2e885aa114eb08391db13dc13ea78be503a582b015fda88738774b` | 3 parts (1–60, 61–120, 121–180) |
| `EV/coordinator/restricted-files-pending-20261029.md` | `c405c38194a3a3535b275d84e458964b9f71ce50fd058339ac57c8c54e025609` | 1 part (1–60) |
| `EV/coordinator/restricted-files-pending-20261101.md` | `84ab3e1f4c5824a3fd97f8a742a293737deabc680d674724e7e6f2cf4dfc00f5` | 1 part (1–60) |
| `EV/coordinator/restricted-files-pending-20261106.md` | `cacdb34097d9c2ae8386dc025b40020611d45b018d1f4b20a71b313f62f2167f` | 1 part (1–60) |
| `EV/coordinator/restricted-files-pending-20261106b.md` | `6d333ed13c563d1d0ccd80c26fbc349e31fdafd5822e7172c7b1c5174b8e3d89` | 1 part (1–60) |
| `EV/coordinator/restricted-files-pending-20261106c.md` | `db19d9549386df451887e4fde06a29e83e16f23f4f1052176b5c88a5961ce8d8` | 1 part (1–60) |
| `EV/coordinator/restricted-files-pending-20261106d.md` | `5203b47108b974960b16a58274dbfaebc5712c5a7405b1927dca3a645645f01e` | 1 part (1–60) |

**Correction to the history (r2 low 13).** The lane's command-only
`I/freeze-job-list-reads.txt` confirms §13.1's part counts: 13, 2, 1, 1,
2 and 1. Its entry-c reads cover 1–60 and 61–121, so the latter part
exceeded the 60-line limit by one line. Section 13.1 now states that
explicitly and no longer claims every part met the limit. The trace
contains commands, not their displayed output. Fix round 1's
`.sm2-fix-scratch/reads.md` lists its seven restriction paths, without
part sizes or boundaries; it cannot independently establish that round's
reported at-most-30-line parts or complete displays. Section 13.6 now
distinguishes its report from what that log can verify.

**Lane-fetched ACS documentation.** `I` is
`EV/mortality-groups-financing-20261021/builds/sm2-fix-r2-inputs`.
The lane retrieved the originals on 6 November 2026, with UTC times,
URLs, sizes and hashes in its manifest; this job fetched nothing. It
compared only `SCHL`, `HISP` and `RAC1P` codes/labels against §8.2 and
read the variable-changes text. All three lists match the crosswalk;
2020's code-list item closes. The experimental-weight distinction stays
explicit. Section 8 changes only that ACS provenance/closure paragraph,
including preservation of the `AGEP`/`SSP` fit-job checks; no category,
column, reference or mapping changes. The PDF below received a hash
check only; the job read its lane-supplied text conversion.

| File in `I/acs-2020-docs/` | URL | SHA-256 | Reliance |
|---|---|---|---|
| `PUMS_Data_Dictionary_2020.txt` | https://www2.census.gov/programs-surveys/acs/experimental/2020/documentation/pums/PUMS_Data_Dictionary_2020.txt | `eab88ac77bc2df8273409a85b841c9ea18879982f575eb15cedf6ee3c965e6e3` | Code/label comparison |
| `ACS2020_PUMS_Variable_Changes_and_Explanations.pdf` | https://www2.census.gov/programs-surveys/acs/experimental/2020/documentation/pums/ACS2020_PUMS_Variable_Changes_and_Explanations.pdf | `698c4cb6dc09bb0191c12352b710939585e86d8993683cbcac49e1118f3acd24` | Lane-fetched original; hash check only |
| `ACS2020_PUMS_Variable_Changes_and_Explanations.pdf.txt` | https://www2.census.gov/programs-surveys/acs/experimental/2020/documentation/pums/ACS2020_PUMS_Variable_Changes_and_Explanations.pdf | `a4d94973c3d4416b6e1dd9a871541b953377a99f3ef006b689a94213de24b9a4` | Experimental weights and variable changes; local text conversion |
| `MANIFEST.tsv` | Lane manifest for https://www2.census.gov/programs-surveys/acs/experimental/2020/documentation/pums/ | `b1f0b4e6d4673f7caa75236e3e06b8850db2c47fe6962a85f3bab9e1fe93e445` | URLs, retrieval times, sizes and hashes |

**Other outside-repository opens, including hash checks and the required
mutant runner.** The scratch read log records repeats and bounded ranges;
this inventory names every distinct explicit outside file. Python's
standard library, pytest/Hypothesis and their runtime imports are runtime
dependencies, not additional source evidence.

- `/Users/maxghenis/microcosm-launch-evidence/dynasim-parity-20260909/RESTRICTED-FILES.md`
- `/Users/maxghenis/microcosm-launch-evidence/dynasim-parity-20260909/coordinator/restricted-files-pending-20261024.md`
- `/Users/maxghenis/microcosm-launch-evidence/dynasim-parity-20260909/coordinator/restricted-files-pending-20261025.md`
- `/Users/maxghenis/microcosm-launch-evidence/dynasim-parity-20260909/coordinator/restricted-files-pending-20261025b.md`
- `/Users/maxghenis/microcosm-launch-evidence/dynasim-parity-20260909/coordinator/restricted-files-pending-20261025c.md`
- `/Users/maxghenis/microcosm-launch-evidence/dynasim-parity-20260909/coordinator/restricted-files-pending-20261029.md`
- `/Users/maxghenis/microcosm-launch-evidence/dynasim-parity-20260909/coordinator/restricted-files-pending-20261101.md`
- `/Users/maxghenis/microcosm-launch-evidence/dynasim-parity-20260909/coordinator/restricted-files-pending-20261106.md`
- `/Users/maxghenis/microcosm-launch-evidence/dynasim-parity-20260909/coordinator/restricted-files-pending-20261106b.md`
- `/Users/maxghenis/microcosm-launch-evidence/dynasim-parity-20260909/coordinator/restricted-files-pending-20261106c.md`
- `/Users/maxghenis/microcosm-launch-evidence/dynasim-parity-20260909/coordinator/restricted-files-pending-20261106d.md`
- `/Users/maxghenis/microcosm-launch-evidence/dynasim-parity-20260909/mortality-groups-financing-20261021/builds/sm2-review-r2.md`
- `/Users/maxghenis/microcosm-launch-evidence/dynasim-parity-20260909/mortality-groups-financing-20261021/builds/sm2-fix-r2-inputs/acs-2020-docs/MANIFEST.tsv`
- `/Users/maxghenis/microcosm-launch-evidence/dynasim-parity-20260909/mortality-groups-financing-20261021/builds/sm2-fix-r2-inputs/review-scripts/nhis2018_adult.txt`
- `/Users/maxghenis/microcosm-launch-evidence/dynasim-parity-20260909/mortality-groups-financing-20261021/builds/sm2-fix-r2-inputs/review-scripts/nhis2018_survey.txt`
- `/Users/maxghenis/microcosm-launch-evidence/dynasim-parity-20260909/mortality-groups-financing-20261021/builds/sm2-fix-r2-inputs/acs-2020-docs/PUMS_Data_Dictionary_2020.txt`
- `/Users/maxghenis/microcosm-launch-evidence/dynasim-parity-20260909/mortality-groups-financing-20261021/s0_1-sources/nchs_lmf_public-use-linked-mortality-files-data-dictionary.txt`
- `/Users/maxghenis/microcosm-launch-evidence/dynasim-parity-20260909/mortality-groups-financing-20261021/s0_1-sources/nchs_lmf_public-use-linked-mortality-file-description.txt`
- `/Users/maxghenis/microcosm-launch-evidence/dynasim-parity-20260909/mortality-groups-financing-20261021/builds/sm2-fix-r2-inputs/acs-2020-docs/ACS2020_PUMS_Variable_Changes_and_Explanations.pdf.txt`
- `/Users/maxghenis/microcosm-launch-evidence/dynasim-parity-20260909/mortality-groups-financing-20261021/builds/sm2-fix-r2-inputs/review-scripts/joint_uncertainty.py`
- `/Users/maxghenis/microcosm-launch-evidence/dynasim-parity-20260909/mortality-groups-financing-20261021/builds/sm2-fix-r2-inputs/review-scripts/check_math.py`
- `/Users/maxghenis/microcosm-launch-evidence/dynasim-parity-20260909/mortality-groups-financing-20261021/builds/sm2-fix-r2-inputs/freeze-job-list-reads.txt`
- `/Users/maxghenis/reviews/uk-hub/tools/run_capped.py`
- `/Users/maxghenis/microcosm-launch-evidence/dynasim-parity-20260909/mortality-groups-financing-20261021/builds/sm2-fix-r2-inputs/pr-595-body-before.md`
- `/Users/maxghenis/microcosm-launch-evidence/dynasim-parity-20260909/mortality-groups-financing-20261021/builds/sm2-fix-r2-inputs/acs-2020-docs/ACS2020_PUMS_Variable_Changes_and_Explanations.pdf`

- `/Users/maxghenis/microcosm-launch-evidence/dynasim-parity-20260909/mortality-groups-financing-20261021/s0_1-sources/nchs_nvsr75-05.txt` (masked table-note phrase contexts, to preserve meaning while changing passive quotations).
- `/Users/maxghenis/microcosm-launch-evidence/dynasim-parity-20260909/mortality-groups-financing-20261021/s0_1-sources/cbo_41681.txt` (masked pp. 1–2 phrase contexts, for the same style check).

**Repository reads.** This record; S0.1 audit section 2; lane design lines
880–920; `life_table.py` lines 13–51, 143–177 and 181–203; and the
path-only fix-round-1 read log. The final edit also checked S0.1's
authority header (lines 1–60). The life-table read included its printed
TR example constants; none enters this record or the PR body. The job
read neither an additional repository source file nor a survey record.
One overlarge documentation-context display truncated; the job opened
no saved copy and reread the relevant age, pooling and crosswalk parts
in smaller selections. Its visible portion included published survey
counts and ACS income bounds; none enters this record or the PR body.

**Checks run.** The two §9.7 blocks extracted by that section's exact
command pass 13 pytest cases; CI does not run them. All three required
mutants produced named failing pytest tests under `run_capped.py` with
1.5 GB RSS and 300 seconds: contrast barring, intersection aggregation,
and removal of race e65's joint dependency. The job restored the
unmutated generator from the record. The component-only eligibility
table matches the review's needed-bound counts; option (b)'s eight age
limits do not alter this table, which resolves other issues by definition.
The scratch `invented_checks.py` passes eight check groups for endpoints,
the age-adjusted Poisson estimator and option (b), non-unit-HR
extraction-to-e65 construction, both directions of joint propagation,
same-quarter exposure, the identification null direction, singleton
handling and the rate-transformation domain. The unchanged review
`joint_uncertainty.py` also runs on invented inputs in scratch. These
checks support formula/design choices; they implement no loader or fit.
The job runs no `tests/mortality_ses` test and makes no tier recount:
only this Markdown record changes, with two embedded Python blocks and
no repository module or test file.

**Choices and remaining limits.** The job chose a monotone first-order
quantile domain and separate endpoint jackknives; neither establishes
nominal Bonferroni coverage. It chose option (b) for unidentified public
85+ interview ages, M-H2 and H-TIME for same-quarter events, existing
`SOURCE_UNAVAILABLE` for identification/design/date stops, normalized
SVD rank tolerance `1 × 10⁻¹⁰`, exact Rao–Wu rescaling with a singleton
stop, and no interior-year NCHS admission fallback. These freeze choices
before outcomes and tighten support, precision and availability checks.
All three component closure routes require recorded amendments; a
closure after outcomes takes a new ledger version preserving the first
attempt. **Reading for the next review:** inconclusive SM2 hands on
intervals naming both omitted components, while §10's weak-power and
failed-gate scopes stay unchanged (§9.3, §9.5). No outcome can settle a
limit in this job; source uncertainty, unsupported ages, joint feasibility
and nominal coverage remain limits as their operative sections state.
