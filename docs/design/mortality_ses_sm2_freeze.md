# SM2 freeze: sources, mappings, joint route, paths and conformance

*Design record, 1 November 2026, branch `mgf-sm2-freeze-20261101`, written
from `origin/master` `1808285925a069143047ae7e7bb2412012db0ad7` by the
mortality, groups and financing lane's SM2 freeze job (Subfleet build,
Claude Code, Opus 5.5).*

## 1. Status and authority

**This record freezes SM2 under section 5.1 of the lane design**
(`docs/design/mortality_groups_financing.md`): "Source hashes, module
versions, seeds, populations, estimands, tolerances and alternatives are
frozen before any real-data outcome is computed." **It is not a
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
  the places section 2's table names, and loosens nothing.
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
  Every number in it is a year, an age, a page, a count of table cells,
  targets, PDF objects or drawing operators, a code from a codebook, a
  tolerance the design or S0.1 sets, a rule or seed this record sets, or a
  constant it derives from those (the Bonferroni critical value).
- **Data.** This job opened no PSID, HRS, SIPP or NHIS microdata file and
  computed nothing on real data. PSID use follows the project's
  data-access record. This record uses and compares no DYNASIM, Urban
  Institute or PWBM material, which reaches these gates only through a
  validation lane (S0.1 scope). CBO publication 49659 stays closed; its
  methods count as
  open until a validation lane supplies a bounded definitions-only
  extract.
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
| S2-02 | 440 | **[open]** availability of earlier NCHS education editions | Settled by the NVSR listing and twelve earlier *Deaths: Final Data* reports: 2010–2017 cover reporting states only (31 rising to 49 states plus DC); 2018–2020 are national in the internet tables I–7 and I–19; 2021–2022 are national in printed Table 14 and Table VIII; the listing of 1 November 2026 holds no edition for 2023. The fit uses 2018–2022; 2010–2017 form a labeled sensitivity | §3.2 | frozen here |
| S2-03 | 474 | **[open]** harmonization of earlier NHIS years | Rescoped to NHIS 2009–2018 sample adults. The 2009, 2016 and 2018 layouts carry `EDUC1`, `HISPAN_I`, `RACERPI2`, `AGE_P`, `SEX`, `SRVY_YR`, `INTV_QRT` and `HHX`/`FMX`/`FPX` with identical code lists; the design variables are `STRAT_P`/`PSU_P` in 2009 and `PSTRAT`/`PPSU` in 2016 and 2018. The fit job checks each intervening year's layout against these names before use | §3.4 | frozen here (window and variables); intervening layouts checked by the fit job |
| S2-04 | 481 | **[open]** a three-dimension joint gradient conditional on lifetime earnings | Resolved by the joint route: joint marginal calibration on a public reference population, with the earnings–education–race dependence taken from a stated proxy. The dependence itself stays unidentified in public data, and §6.4 says so | §6 | frozen here (route); the dependence stays unidentified and named |
| S2-05 | 511 | **[open mapping]** Cristia's odds ratios | Frozen: predicted probabilities on a named reference population, then ratios to `q3`'s probability. Cristia enters only as a sensitivity and a source reported beside the fit; no log odds ratio enters as a log relative risk | §4.4 | frozen here |
| S2-06 | 520 | **[proposed]** CBO 41681 as context only | Confirmed. It supplies the reason the widening alternative leaves race and Hispanic origin flat (pp. 1–2) and no coefficient or target | §3.1, §7.4 | frozen here |
| S2-07 | 538 | **[proposed schema]** dimensions, columns, categories, references and unclassified treatment | Confirmed against `mortality_ses/specification.py`; tightened to one unclassified string per dimension, a fixed category order, and a crosswalk per source | §8 | frozen here |
| S2-08 | 564 | **[proposed loader]** OACT contrasts `log(r_q) − log(r_q3)`, band expansion, a source-year matrix that says what happens before a band first appears | Confirmed; tightened with the band-backcast rule, the figure-year rule and two independent table transcriptions | §3.1, §4.1, §5 | frozen here |
| S2-09 | 570 | **[open]** earnings ages below 62 and 90–120 | Frozen: the 62–64 coefficient holds down to age 25 and the age-25 value below; the 85–89 coefficient holds up to 120; four registered sensitivities | §5 | frozen here |
| S2-10 | 579 | **[open]** terminal 100+ rule and any unsupported other-group coefficient | Frozen: race contrasts at 100–120 hold the age-99 contrast, and the fit reads no contrast from the 100+ interval; `other_non_hispanic` comes from NHIS–LMF, with NCHS's AIAN and Asian tables reported beside as a partial group | §4.3, §5 | frozen here |
| S2-11 | 587 | **[open]** extraction and digitization of the 2022 gradient, its uncertainty, complete coverage | Frozen: vector extraction of Study 129 Figures 7–12, validated against Tables 7–12 at every table year, with a digitization half-width the validation sets; complete tables at every knot | §7.1–7.3 | frozen here |
| S2-12 | 591 | **[open]** widening `CoefficientPath`: slope, origin, ages, caps; knot years and synchronization | Frozen: origin 2024, slopes from a frozen estimator on OACT's pre-pandemic annual figures, caps of 30 years and a 1.5 multiplier, race held flat; annual knots 2010–2024 with one synchronization rule | §7.4–7.5 | frozen here |
| S2-13 | 602 | **[proposed]** `unclassified_rule="reference"` for SM3's overall denominator | Confirmed for SM3; `refuse` for conformance runs and for any projection until the frame carries the attributes | §8.3 | frozen here |
| S2-14 | 606 | **[open: identification]** marginal contrasts do not determine mutually adjusted coefficients; freeze a joint route and its reference distribution | Five candidate routes and one unavailable route; primary JR-C; JR-A (plain addition, labeled), JR-B, JR-D and JR-E as sensitivities. NHIS targets compare as age-standardized hazard ratios on `R_ref(t)`'s single-age population, under named assumption M-H1 (§4, §4.5) | §4, §6 | frozen here |
| S2-15 | 629 | **[open]** exact release dates of any earlier NHIS cohort used | Left open. The linked-mortality `.dat` files carry the listing date 26 April 2022; each NHIS year's release date settles from that year's survey description, which the fit job records. Nothing in SM2 depends on it, because SM2 claims no prospective origin | §3.4 | left open; settled by the fit job's per-year release ledger |
| S2-16 | 641 | **[frozen tolerance; proposed operationalization]** e65 target from source ratios on one baseline, with a fixed reference population, marginalization and tail rule | Frozen; the 0.1-year limit stays | §9.2 | frozen here (operationalization); tolerance frozen, S0.1 §2.5 |
| S2-17 | 649 | **[open]** whether the different source populations and baselines can satisfy the targets together | This record freezes the procedure: one joint calibration per knot on one reference population, and a named failure when it cannot reproduce every target. Whether it can is an outcome, so this record does not settle it | §6.3, §9 | left open; settled by the fit under §9's rule |
| S2-18 | 659 | **[open until the loader plan is frozen]** the critical family's integer size and which joint-survey targets it holds | Frozen: **6,884** targets, itemized | §9.4 | frozen here |
| S2-19 | 677 | **[proposed named procedure]** `SM2_SOURCE_RECONSTRUCTION_AND_CLUSTER_BOOTSTRAP` | Filled in step by step | §9 | frozen here |
| S2-20 | 688 | **[proposed suppression]** at least 100 unweighted persons per published microdata subgroup | Confirmed and tightened: also at least 20 deaths in any published death-based cell, and the rule applies to ACS as well as NHIS aggregates | §11.5 | frozen here |
| S2-21 | 353 | Unmarked: CBO 49659's "safely bounded definitions remain open" | Left open as the brief requires; SM2 uses no part of 49659 | §3.1 | left open; settled by a validation lane's definitions-only extract |
| S2-22 | 523 | Unmarked: "CBO 49659's mixed-source methods remain open pending a safely bounded definitions-only extract" | Same item as S2-21 | §3.1 | left open; as S2-21 |
| S2-23 | 588 | Unmarked: "A 2020 table-only path is a proposed registered sensitivity" | Confirmed as sensitivity P-TABLE; it cannot become primary without amending Q6 | §7.3 | frozen here |
| S2-24 | 669 | Unmarked: a source that does not publish the uncertainty a target needs leaves that item "open or inconclusive" | Applied: OACT publishes no deaths or exposures, so OACT's random-variation component stays open, and every OACT e65 member stays inconclusive (or fails, if its point residual lies outside ±0.1 year) until the component closes. That keeps lifetime earnings, and with it SM2 as a whole, from admission. A Poisson approximation from `R_ref`'s recipients is reported beside, labeled as likely understating the variation, and changes no verdict | §9.3, §9.5, §10 | left open; settled by OACT exposure or death counts by sex × band × quintile × year |
| S2-25 | 698 | Unmarked: "`SOURCE_UNAVAILABLE` / open identification applies to the complete modern three-dimension joint source and missing source-age mappings" | Each trigger and fallback stated | §10 | frozen here |

**Counts.** Of the 25 rows, this record freezes 20 and leaves 5 open, each
with what settles it (S2-15, S2-17, S2-21, S2-22, S2-24); none goes to Max.
S2-24's open item keeps lifetime earnings inconclusive, and with it SM2's
admission, until OACT's counts close it (§9.3). S2-03 carries a check the
fit job performs. Section 12 holds two rules for cases outside this table.

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
(§9.4), and §5 names the alternative. The fit records, and never fits, a
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
  2021 titles only; the fit job's loader checks every year's layout.
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
  them before use.
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
  depend on the group (p. 53).
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
  S2-15); the fit job records each from that year's survey description.

### 3.5 Reference population and baseline

- **Reference population (reference, not a target) [frozen here].** The
  Census Bureau's ACS 1-year PUMS person files for each knot year
  2010–2024, with their person weights and replicate weights. NCHS built
  its 2020 education denominators from the 2020 1-year PUMS (NVSR 72(10)
  internet tables, p. 2), and the fit uses that file too; the fit job
  records any data-quality note the Census Bureau attaches to it. §6
  defines the population built from these files. This job opened no ACS file
  or ACS documentation and did not check their URLs (§11.6).
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
so any fixed standard returns it. The sources read here give no reason to
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
  at younger ages move into lower quintiles at older ages (p. 2). SM3's
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
  held constant over time. An NHIS hazard `μ` maps to an annual probability
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
  `q`, so it supplies no target (§5).
- **M-R4, `other_non_hispanic`.** NHIS–LMF supplies the marginal hazard
  ratio against `white_non_hispanic` at attained ages 25–44, 45–64,
  65–74, 75–84 and 85+, by sex, pooled and held constant over time (fit).
  Beside it, for 2019–2024, the record reports `ln` of the ACS-weighted
  average of the AIAN and Asian NH `q` over the NH white `q`, labeled
  "partial group: no NHPI, multiracial or other people".
- **M-R5, bridged and single race (assumption).** 2010–2017 contrasts are
  bridged-race; 2018 onward are single-race; Hispanic origin does not
  change (NVSR 75(5) pp. 1–2, 54). SM's categories follow the single-race
  definitions (§8.2), and every path labels the 2017–2018 break.
- **M-R6, ratios to the total population.** For the e65 target only
  (§9.2), each group's `q` divides by the NCHS total-population `q` at the
  same age and year.
- **Properties the source states and every report repeats:** the
  misclassification adjustment, the Medicare supplement at 66–99 for
  three groups only, modeled old-age mortality for the other groups, and
  smoothing above about 85 (§3.3).

### 4.4 Cristia's odds ratios (sensitivity and beside only)

**Log odds ratios never enter as log relative risks.** Cristia's models
predict death in the next year with the bottom quintile as reference
(p. 18). Tables 5–6 hold, for each sex and age range, a column with age
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
  sample keeps ages 35–75 only (p. 8); this record reads it as 35–49 and
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
  (p. 14). Contrasts against a reference category are differences of
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
- **Time at risk.** From the middle of the interview quarter
  (`SRVY_YR`, `INTV_QRT`) to the middle of the death quarter (`DODYEAR`,
  `DODQTR`) for `MORTSTAT = 1`, or to 31 December 2019.
- **Attained age.** `AGE_P` plus elapsed time. Because NHIS suppresses
  birth dates, the estimator splits each person-year across attained ages
  on the assumption that birthdays fall uniformly through the year. A person
  with `AGE_P = 85` (85 or older at interview) contributes only to the
  85+ band, the one band whose lower bound such a person surely meets.
- **Model.** For each sex, band and dimension, a survey-weighted Poisson
  regression of deaths on that dimension's category indicators and
  single-year attained-age indicators, with log person-years as offset.
  In the 85+ band the age terms are indicators of attained ages 85–89,
  90–94 and 95+ for persons interviewed below 85, and one indicator per
  completed year since interview for persons top-coded at interview. The
  exponentiated category coefficients are the marginal hazard ratios.
- **M-H1, proportional hazards within a band (assumption).** The model
  gives each category one hazard ratio per band, so it assumes that ratio
  holds at every attained age in the band. In the 85+ band the assumption
  covers ages 85–120, including the ages that NHIS sees only through its
  95+ indicator and through persons top-coded at interview. §4's common
  scale compares this ratio with an age-standardized model ratio, and
  §11.7 tests that the two agree whenever the model's hazards are
  proportional.
- **Missing values.** `EDUC1` 97–99, `HISPAN_I` 11 and any race code that
  §8.2 leaves unclassified drop out of that dimension's estimate only,
  and the fit reports their counts.
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
| Lifetime earnings | 62–89 (bands 62–64 to 85–89, with backcasts before 2015 and 2020, §3.1) | `TAIL_E_HOLD_62_64_DOWN`: ages 25–61 take the 62–64 coefficient; ages 0–24 take the age-25 value | `TAIL_E_HOLD_85_89_UP`: ages 90–120 take the 85–89 coefficient | T-E1: ages 25–61 take the 65–69 coefficient instead, which avoids the early-claimer selection the source describes for 62–64 (Study 129 p. 6). T-E2: Cristia age shape (below). T-E3: a linear taper of each log contrast from its 85–89 value at age 89 to zero at age 110, and zero above, labeled "assumed convergence, not a finding" (the source reports narrower spreads at older ages, pp. 2, 8, but no rate). T-E4: every OACT band shifted one year younger (M-E5) |
| Education | 25–64 (NCHS bands); 65–74, 75–84 and 85+ (NHIS–LMF) | `TAIL_D_HOLD_25_DOWN`: ages 0–24 take the 25–34 coefficient | The 85+ band runs to 120 | T-D1: ages 65–120 take the 55–64 coefficients, with no NHIS input, to show how much the 65+ coefficients rest on NHIS |
| Race and Hispanic origin: `hispanic`, `black_non_hispanic` | Single ages 0–99 | None needed | `TAIL_R_HOLD_99_UP`: ages 100–120 take the age-99 coefficient; the fit reads no contrast from the "100 and older" interval | T-R1: a taper from the age-99 value to zero at age 110, labeled as T-E3 |
| `other_non_hispanic` | 25–44, 45–64, 65–74, 75–84, 85+ (NHIS–LMF) | `TAIL_O_HOLD_25_DOWN`: ages 0–24 take the 25–44 coefficient | 85+ runs to 120 | T-R2: for 2019–2024, the partial AIAN-and-Asian composite (M-R4) replaces NHIS at every age, labeled "partial group" |

- **T-E2, Cristia's age shape.** For each sex and non-reference quintile
  `k`, let `c_b(k)` be Cristia's marginal log contrast against `q3` in age
  range `b` (M-C2). Ages 50–61 take the 62–64 coefficient times
  `c_50–64(k) / c_65–75(k)`, and ages 25–49 times
  `c_35–49(k) / c_65–75(k)`. The pooled least-squares slope over
  the four quintiles replaces a ratio when `|z| < 2` for the quintile's
  65–75 odds ratio, and every ratio stays within `[0.5, 3]`; this record
  fixes both guards to keep a ratio of small numbers from driving the
  sensitivity.
- **Ages under 25.** NCHS leaves out ages below 25 because people that
  young may not have finished their education (NVSR 74(4) p. 127); SM3's
  earnings proxy counts income from age 22 (S0.1 §1.2); and SM3's
  population starts at 50.
  The held values below 25 exist because SM1's table must be complete; a
  frame that classifies a person under 25 on either dimension must
  register that use first (§8.3).
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
  top-and-bottom-coded-values CSV, which the fit job records). A record at
  or above its state's threshold stands for every age from the threshold
  to 120: the fit spreads its weight over those single ages in proportion
  to the stationary person-years `Lx` of the TR 2026 `q` for that sex and
  year, and each spread row keeps the record's other attributes. Below the
  threshold, `AGEP` is the single age.
- **Education and race and Hispanic origin.** From the ACS education,
  Hispanic-origin and race items through the crosswalk in §8.2.
- **A lifetime-earnings quintile proxy `Q̃`.** At ages 62–89, among
  persons with positive Social Security income, `Q̃` is the weighted
  quintile of that income within sex and single age; the construction splits
  weight that straddles a quintile boundary so each quintile holds exactly
  one fifth.
  This is the public stand-in for OACT's AIME quintile (M-E3, M-E4): both
  rank people within sex and single age, and both rank by a quantity tied
  to the worker's benefit (OACT notes that ranking by AIME or by PIA is
  equivalent within a birth year, Study 129 p. 2, note 2).
- **The dependence model.** On persons with positive Social Security
  income aged 62–84, for each sex and age group `G ∈ {62–69, 70–79,
  80–84}`, a weighted ordered logit
  `P(Q̃ ≤ k | d, r, a) = expit(c_k(a) − λ_D,G[d] − λ_R,G[r])`,
  with `λ_D[high_school] = λ_R[white_non_hispanic] = 0` and cut points
  by single age. Ages 85 and over use `G = 80–84`; ages below 62 use
  `G = 62–69`.
- **The joint weights.** At sex `s`, age `a` and year `t`,
  `w(k, d, r) = P(d, r | s, a, t) × P(k | d, r)`: the first factor is the
  ACS weighted share among all persons; the second comes from the ordered
  logit with cut points `c_k(s, a, t)` recomputed so that, at ages 62–89,
  every quintile holds exactly one fifth of the subpopulation with positive
  Social Security income (OACT cuts its quintiles at fifths of the records
  at each age, though their exposure shares can differ slightly, pp. 3–5),
  and at other ages one fifth of the whole
  population. Persons without Social Security income at 62–89 take
  `P(k | d, r)` from the same model. The fit
  evaluates OACT targets on the subpopulation with positive Social
  Security income (its own `P(d, r | s, a, t)`, the same `P(k | d, r)`);
  every other target on the whole population.
- **What the proxy is not.** A benefit amount is not an AIME. Study 129
  itself names two reasons they part: a worker who claims at 62 takes a
  larger reduction than one who waits (p. 7), and dually entitled
  beneficiaries receive a partial spouse benefit on top of their own
  (p. 8, note 1). This job did not read the ACS documentation, so it
  makes no claim about which benefit types the ACS income item covers;
  the fit job reads each year's data dictionary and records that
  definition before building `Q̃` (§11.6). §6.6 lists what the gap leaves
  unidentified.

### 6.3 Joint marginal calibration [frozen here]

For each knot `t` and sex `s`, the unknowns are:

| Block | Unknowns | Targets |
|---|---|---|
| Lifetime earnings | 4 non-reference quintiles × 6 bands = 24 | 24 OACT contrasts (M-E1), including backcast copies (§3.1) |
| Education, 25–64 | `less_than_high_school` and `some_college` per NCHS band (8), plus one split `δ_s`, with `college = some_college + δ_s` in every band | 4 bands × 2 NCHS contrasts (M-D1, M-D2) plus the NHIS split (M-D3) = 9 |
| Education, 65+ | 3 non-reference categories × 3 bands = 9 | 9 NHIS contrasts (M-D4) |
| `hispanic`, `black_non_hispanic` | 2 × 100 single ages = 200 | 200 NCHS contrasts (M-R1) |
| `other_non_hispanic` | 5 bands | 5 NHIS contrasts (M-R4) |

That is 247 equations in 247 unknowns per knot and sex. Coefficients at
ages outside these blocks follow §5. The fit computes each target's implied
value by expanding `R_ref(t)` into
rows, one per (quintile, education,
race) combination at each single age, with weight `w`, applying the
candidate coefficients and SM1's `normalize_probabilities` cell by cell
against the baseline `q`, and averaging the normalized probabilities over
the target's ages and subpopulation: crude for OACT and NCHS targets, and
age-standardized hazards for NHIS targets (§4, common scale).

- **Solver.** Newton's method on the full system, started from the
  plain-addition coefficients (JR-A); convergence when every implied
  target is within `1 × 10⁻¹⁰` of its target in log units. A second start
  from all-zero coefficients must reach the same solution within
  `1 × 10⁻⁹`.
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
| **JR-F: PSID reference population (not available)** | As JR-C, with the deployment population's own joint distribution | The PSID cohort's lifetime-earnings × education × race distribution | — | — | PSID use follows the project's data-access record. This record does not use it; §12 states the rule for the primary |

**JR-D's definition [frozen here].** For dimension `X`, sex `s` and
Cristia age range `b`, `κ_X(s, b)` is the weighted least-squares slope,
through the origin, of Cristia's conditional log contrasts (M-C3) on its
marginal log contrasts (M-C2 for earnings, M-C5 for education and race),
across the dimension's non-reference categories, with weights equal to
the categories' shares in Cristia's Table 1 where it prints them and
equal weights otherwise; `κ` stays within `[0, 1]`. JR-D's coefficients
are `κ` times JR-A's, and ages outside 35–75 take the nearest range's `κ`.

### 6.5 Choice

**Primary: JR-C.** Sensitivities: JR-A (labeled "plain addition of
marginals"), JR-B (JR-C with `λ = 0`), JR-C with `λ` scaled by 0.5 and by
1.5, JR-D and JR-E. Reasons:

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

### 6.6 What stays unidentified

- **The dependence between OACT's AIME quintile and education or race.**
  The Social Security income quintile stands in for it. Benefits that do
  not follow the worker's own AIME move the proxy away from OACT's
  quintile: claiming-age reductions (Study 129 p. 7), spouse benefits for
  the dually entitled (p. 8, note 1), and any benefit type the ACS item
  covers that OACT's population excludes (M-E4; the item's definition is
  the fit job's to record, §6.2). No public source settles which way
  these move the estimated dependence.
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

Every knot also carries the NHIS-based targets (education at 65+, the
split, `other_non_hispanic`). "Held" means the fit imposes the same
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
| Earnings slope `g_E(s, B)` | For each sex and OACT band with at least ten annual points in 2005–2019: the least-squares slope, over those years, of `S(t) / S̄`, where `S(t) = L_E(q1)(t) − L_E(q5)(t)` from the annual figures and `S̄` is its mean over the same years. Bands with fewer points (80–84, five points; 85–89, none) take the pooled slope of 70–74 and 75–79 for the same sex. Ages outside 62–89 take the nearest band's slope | Study 129 calls the gradient's trends "generally, slowly growing" (p. 10); 2005–2019 are the fifteen pre-pandemic years with at least three bands present, and the estimator leaves out the pandemic years because of p. 9 |
| Negative slopes | Set to zero: no widening for that sex and band, which then equals P-PRIMARY | The alternative is a widening path; a fitted narrowing is not evidence for it |
| Education slope `g_D(s)` | `g_E(s, 62–64)` | No national education series longer than five years exists (§3.2); 62–64 is the earnings band nearest NCHS's ages |
| Race and Hispanic origin | `m(t) = 1`, held flat | CBO 41681 describes differences between black and white Americans narrowing over time (pp. 1–2); no source here supports a widening race path |
| Ages | Every age 0–120 (the tails follow §5's rules applied to the multiplied coefficients) | One rule for the whole table |
| Caps | The multiplier stops growing after 30 years (2054) and never exceeds 1.5 | The source series spans 1995–2022, about 30 years; the alternative carries no trend further than the data it comes from |

The path's `years` are P-PRIMARY's knots plus 2025–2054; every later year
returns the 2054 table. SM1 revalidates each returned table and still
normalizes every cell (Q4), so widening moves deaths between groups and
never adds deaths. The fit job computes the slopes under this
frozen estimator; this record computes none.

### 7.5 Synchronization

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

| `name` | `column` | `categories`, in this order | `reference` | `unclassified_values` |
|---|---|---|---|---|
| `lifetime_earnings` | `sm_lifetime_earnings_quintile` | `q1`, `q2`, `q3`, `q4`, `q5` (lowest to highest) | `q3` | `("unclassified",)` |
| `education` | `sm_education` | `less_than_high_school`, `high_school`, `some_college`, `college` | `high_school` | `("unclassified",)` |
| `race_hispanic_origin` | `sm_race_hispanic_origin` | `hispanic`, `white_non_hispanic`, `black_non_hispanic`, `other_non_hispanic` | `white_non_hispanic` | `("unclassified",)` |

### 8.2 Crosswalks [frozen here]

**Education.**

| SM category | Meaning | NCHS death certificate | NHIS `EDUC1` | ACS | SM3's PSID years (S0.1 §1.2) |
|---|---|---|---|---|---|
| `less_than_high_school` | No high school diploma or GED | "Less than high school diploma or GED" | 00–12 | Below a regular diploma or GED | Fewer than 12 |
| `high_school` | Diploma or GED, no college | "High school diploma or GED" | 13–14 | Regular diploma or GED | 12 |
| `some_college` | Some college without a degree, or an associate degree | Within "Some college or collegiate degree" | 15–17 | Some college, associate degree | 13–15 |
| `college` | Bachelor's degree or higher | Within "Some college or collegiate degree" | 18–21 | Bachelor's degree or higher | 16–17 (the reader's upper code) |
| `unclassified` | — | "Not stated" | 96–99 | Any code the year's data dictionary leaves without a level (the fit job records them) | Missing |

The ACS column is semantic: the fit job maps each year's education codes
from that year's data dictionary and tests that every code lands in
exactly one category. NHIS codes come from the 2009, 2016 and 2018 person
layouts (pp. 265, 296, 294).

**Race and Hispanic origin.**

| SM category | NCHS life tables | NHIS (`HISPAN_I`, `RACERPI2`) | ACS | Cristia |
|---|---|---|---|---|
| `hispanic` | Hispanic (any race) | `HISPAN_I` 00–10 | Any Hispanic origin | Hispanic |
| `white_non_hispanic` | NH white (single race from 2018; bridged 2010–2017) | `HISPAN_I` 12 and `RACERPI2` 01 | Not Hispanic, white alone | White |
| `black_non_hispanic` | NH black | `HISPAN_I` 12 and `RACERPI2` 02 | Not Hispanic, black alone | Black |
| `other_non_hispanic` | No complete table; AIAN NH and Asian NH (2019–2024) form a partial group | `HISPAN_I` 12 and `RACERPI2` 03–06 (AIAN only, Asian only, not releasable, multiple race) | Not Hispanic, any other race alone or two or more races | Other Race |
| `unclassified` | — | `HISPAN_I` 11 | Any code the year's data dictionary leaves without a group (the fit job records them) | — |

`HISPAN_I` 10 ("type refused") stays `hispanic`, because its label names a
Hispanic person whose type is unknown. Code 11 is `unclassified`, because
the 2018 layout's notes assign it both to Hispanic people whose type was
not ascertained and to people whose origin was not ascertained (2018
Sample Adult layout, p. 8); sensitivity X-R1 treats 11 as `hispanic`. The
public files carry no flag showing whether NCHS imputed race or
ethnicity (2018 survey description pp. 25–26), so the fit cannot set
imputed values apart.

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
| SM2's fit and conformance on `R_ref` | `refuse` | The crosswalk leaves no reference-population person unclassified; one that appears is a construction error |
| SM2's NHIS estimates | Not through SM1 | §4.5 drops unclassified persons from that dimension's estimate and reports the count |
| SM3 | `reference` (confirms S0.1 §2.3) | SM3's estimand keeps unclassified persons in the overall ratio and in no group cell (S0.1 §1.1); under `reference` they take zero log risk on that dimension, SM1 still conserves the cell, and the cell log counts them (`specification.py:219–247`; `normalizer.py:17–35`) |
| Any projection (Track B, the open population) | `refuse` until the frame carries all three attributes and a registration names the rule | `FRAME_ATTRIBUTE_MISSING` (§10) |

A person under 25 classified on lifetime earnings or education needs a
registration of its own before any use (§5).

## 9. Conformance procedure: `SM2_SOURCE_RECONSTRUCTION_AND_CLUSTER_BOOTSTRAP`

**[frozen here]** throughout, unless a step names S0.1. The procedure runs
on P-PRIMARY under JR-C. Sensitivities run the same steps and report;
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
- **The target.** `q_T,g(a) = min(1, q_base(s, a, t) × ρ_g(a))`, with
  `ρ_g` the source's ratio of group `g` to its whole population: for OACT,
  the RMR of `g`'s band at the knot (after backcasts and holds; above 89
  the 85–89 RMR); for `hispanic`, `white_non_hispanic` and
  `black_non_hispanic`, `q_g(a) / q_total(a)` from the knot's NCHS tables
  (M-R6), holding the age-99 ratio above 99; for `other_non_hispanic`, the
  NHIS hazard ratio for `a`'s band times `q_NHW(a) / q_total(a)`.
- **Closing rule.** Both life expectancies come from
  `data/life_table.life_expectancy(q[0..120], 65)`, the backward recursion
  with the constant-terminal-`q` closing at the last age
  (`life_table.py:17–37, 181–203`). The module calls that closing "a
  builder default awaiting ratification" (lines 30–31); this record fixes
  it for SM2's e65 only.
- **The limit.** `|e65(q_F,g) − e65(q_T,g)| ≤ 0.1` year, **the design's
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
| | NCHS life tables | Poisson with expected deaths `q_x × P_x`, where `P_x` is the group's population at age `x` in `R_ref(t)`. The life-table reports print no death counts, so this is a registered approximation, used at the Medicare-supplemented ages too |
| | OACT | **[open]** Study 129 prints rates and RMRs but no deaths or exposures (Tables 1–12), so the source cannot supply this component (row S2-24). It settles when OACT's exposure or death counts by sex × band × quintile × year are available. Until then every OACT e65 member is inconclusive or fails (below) |
| U3, survey sampling | ACS (reference population and NCHS education denominators) | One refit per ACS replicate, with the variance formula that each year's PUMS documentation gives and the fit job records. NCHS's denominators move with the same replicate: each category's share within sex and band is re-tabulated from that replicate and scaled to NCHS's printed total. The fit job also reports the ratio of its replicate standard errors to NCHS's printed ones (Table VIII, I–19) |
| | NHIS–LMF | Rao–Wu rescaled bootstrap: PSUs resampled with replacement within strata, separately for each design period: the 2009 layout's `STRAT_P`/`PSU_P` and the 2016 and 2018 layouts' `PSTRAT`/`PPSU`, with the periods' strata kept distinct; the fit job reads which names each intervening year uses. Resampling whole PSUs keeps every family and every person's whole history together, once the fit job confirms from each year's survey description that families nest within PSUs |
| U4, linkage and perturbation sensitivity | NHIS–LMF | Discrete alternative fits, not draws: NHIS weights replaced by the original sample-adult weight with ineligible persons dropped; `HISPAN_I` 11 coded `hispanic` (X-R1). The fit reports each alternative's conformance; neither gates |

**What OACT's open U2 means [frozen here].** S0.1 keeps a target whose
source does not publish the uncertainty it needs "open or inconclusive",
and it lets no complete-count rate count as free of uncertainty (audit
lines 661–669). Every Monte Carlo draw refits the model to that draw's
targets (§9.4), so a source's random variation moves target and fit
together, but it still reaches an e65 residual through capping,
composition and tails. Leaving OACT's term out would narrow the earnings
e65 bounds and make passing easier, so this record applies S0.1's rule:

- **Every OACT e65 member is inconclusive while the component stays
  open.** The 150 members of e65 by earnings quintile (§9.4) cannot pass:
  one whose point residual lies inside ±0.1 year is inconclusive, and one
  whose point residual lies outside fails (§9.5). The component closes
  only when OACT's deaths or exposure by sex × band × quintile × year
  reach the project, through a recorded amendment (§11.1).
- **What that stops.** Under §9.5 an inconclusive member makes lifetime
  earnings inconclusive, and `WEAK_POWER_OR_VACUITY` blocks that
  dimension's admission (§10). SM2 passes as a whole only when all three
  dimensions pass, so **SM2 cannot earn admission while this item stays
  open**. The fit still runs every step and publishes every member's
  residual and bound, and each dimension's status, so education and race
  and Hispanic origin carry verdicts of their own.
- **The OACT contrast members keep their verdicts.** Each draw refits to
  its own targets, so a contrast member checks the reconstruction (§9.4);
  OACT's random variation does not enter its residual.
- **A Poisson sensitivity, reported and never a verdict.** Beside each
  OACT e65 member, the fit reports a bound with an added Poisson term:
  at each single age of a band, expected deaths equal the target's
  probability times one fifth of that age's Social Security recipients of
  that sex in `R_ref(t)`. It carries the label "likely understates OACT's
  random variation", because `R_ref`'s recipients include beneficiaries
  that OACT's population leaves out (M-E4), which overstates exposure. It
  changes no verdict.
- **Two labels stay.** The lifetime-earnings coefficient intervals that
  SM2 hands to SM3 and SM4 carry "OACT random variation not included",
  and the Study 129 versus Study 124 comparison, which the fit reports,
  cannot trigger `GRADIENT_SOURCES_INCONSISTENT` (§10).

**The engine.**

- **Monte Carlo draws** cover U1, U2 and NHIS's part of U3: `B = 2,000`
  draws, each a full refit of every knot and sex (§6.3) followed by every
  family member's residual. The seed is
  `numpy.random.SeedSequence(2026110101)`, spawned into one child stream
  per component and source in the order of §3's tables.
- **ACS replicates** cover the ACS part of U3: one refit per replicate,
  with the Monte Carlo inputs at their point values.
- **Combination.** For family member `k`,
  `SD_k = sqrt(Var_MC,k + Var_ACS,k)`, treating ACS sampling as independent
  of the other components. NCHS's education denominators are ACS too, and
  they sit inside `Var_ACS` with the reference population.
- **Shared-source covariance.** Each draw perturbs each printed source
  value once, and every target, refit and e65 in that draw uses that same
  value: the `q3` RMR enters four contrasts; an NH white `qx` enters two
  race contrasts and every race e65 target; an ACS replicate enters the
  reference population and NCHS's denominators together.
- **The simultaneous bound.** `r̂_k ± z × SD_k`, with
  `z = Φ⁻¹(1 − 0.025 / 6,884) ≈ 4.486`, the two-sided 95 percent
  Bonferroni bound over the family (§9.4). If a member's Monte Carlo
  draws have skewness above 1 in absolute value, its bound uses the
  first-order Cornish–Fisher quantile `z + (z² − 1) γ / 6` in place of `z`.
- **Monte Carlo error.** For each member, the Monte Carlo standard error
  of the bound's half-width, `z × SD_MC,k / sqrt(2(B − 1))`, must stay under
  one tenth of the member's tolerance `τ_k`: less than 0.01 year for e65,
  and less than `ε / 10` for a contrast. If it is not, `B` doubles, up to
  32,000; if the rule still fails, the member is inconclusive. Tier A has
  no simulation error.

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

- **Joint-survey targets.** The 30 NHIS targets are in the family; they
  are the only survey-estimated targets.
- **One member per published or estimated quantity.** A target imposed at
  several knots (a backcast copy, a held target or an NHIS target) is one
  member, tested by its largest absolute residual across the knots that
  impose it. The e65 targets differ by knot, because the baseline does, so
  each knot's is a member.
- **What the contrast members test.** For a contrast, the residual is the
  model-implied contrast minus the draw's target after that draw's refit.
  Because §6.3's system has as many equations as unknowns, a contrast
  member shows whether every refit reproduces its targets: a
  reconstruction check. The
  e65 members compare two different constructions (the model on the
  reference population against the source's ratios on the baseline), so
  they also test composition, capping and tails.
- **Not in the family.** The sensitivities of §5, §6.5 and §7.3, and the
  sources reported beside the fit.

### 9.5 Pass conjunction

SM2 earns admission, labeled "calibrated, not validated", only if all
of these hold:

1. every tier A check passes (§9.1);
2. every one of the 6,884 members has its simultaneous bound inside
   `±τ_k`, with the Monte Carlo rule met (§9.3);
3. every invariant of §9.6 holds;
4. no condition in §10 blocks.

A member whose point residual lies inside `±τ_k` but whose bound crosses
it is **inconclusive**; a member whose point residual lies outside fails.
An inconclusive member makes its dimension inconclusive (e65 by quintile
and OACT contrasts: lifetime earnings; education contrasts: education;
race contrasts, race e65 and `other_non_hispanic`: race and Hispanic
origin). **A bound too wide to judge never passes.** The record publishes
each dimension's status; SM2 passes as a whole only when all three pass,
because SM1 needs all three. While OACT's random-variation component
stays open, every e65 member by earnings quintile is inconclusive or
fails whatever its computed bound (§9.3), so lifetime earnings cannot
pass, and neither can SM2 as a whole.

### 9.6 Invariants (design §6)

- **Life tables.** Every fitted group life table (`q_F,g` for each knot,
  sex and group) satisfies `data/life_table.py`'s invariants:
  `period_life_table` and `life_expectancy` agree; survivorship and
  person-years are nonnegative and nonincreasing with age; changing the
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

## 10. Named conditions

This record fixes every fallback below now, before any outcome. **Nobody
tunes anything so that sources agree** (S0.1 §2.5, frozen).

| Condition | Trigger for SM2 | What it stops | Fallback |
|---|---|---|---|
| `GRADIENT_SOURCES_INCONSISTENT` | Two comparable sources disagree beyond SM2's fit tolerance. "Comparable": the same SM category definitions and sex, overlapping ages, calendar windows that overlap at least half the shorter one, and populations that differ at most in institutional coverage. Assessed: (a) Study 129 against Study 124 at table years 1995–2015, bands 62–84; (b) NCHS life tables against NHIS–LMF for `hispanic` and `black_non_hispanic` at 25–84. Not assessed: OACT against Cristia (different years, ages and earnings measures), NCHS education against NHIS at 25–64 (their windows share two of NCHS's five years), and `other_non_hispanic` against the partial composite (different groups). Metric: the difference in temporary life expectancy over the pair's shared ages, each built by applying the source's ratios to the TR 2026 baseline of the year compared: for (a), from 62 to the top of the year's oldest band printed in both studies, per table year, sex and quintile (5 × 2 × 5 = 50 comparisons); for (b), from 25 to 85, per NCHS year 2010–2019, sex and group (10 × 2 × 2 = 40). Triggered when a comparison's simultaneous 95 percent bound, Bonferroni over these 90 comparisons, excludes ±0.1 year | Nothing about SM2's admission. OACT stays primary for earnings and NCHS for race; the other source stays a registered sensitivity; the fit's report publishes the disagreement. Pair (a) has no random-variation term (§9.3), so the fit reports a disagreement it finds and it does not trigger | None needed |
| `SOURCE_UNAVAILABLE` | (i) The digitization fails validation, or the digitizer cannot read a figure; (ii) an NHIS or LMF file is missing or its hash differs; (iii) an ACS year is missing; (iv) the ordered logit does not converge; (v) any source file's hash differs from §13 or the fit job's manifest | (i) P-PRIMARY, and with it SM2's admission; (ii) admission of education and race; (iii) one missing year: nothing, the knot uses the nearest year, labeled; two or more: SM2's admission; (iv) JR-C, and with it SM2's admission; (v) the run | (i) P-TABLE, computed and published labeled, never substituted; the Q6 question goes to Max (§12). (ii) T-D1 for education at 65+, Cristia's conditional `college`/`some_college` contrast for the split, T-R2 for `other_non_hispanic` at 2019–2024 only (earlier knots then have no `other_non_hispanic` source and the report marks them unavailable); all labeled, none admitted. (iv) JR-B, labeled, not admitted |
| `EXPOSURE_UNRESOLVED` | Any report calls a comparison with a source reported beside the fit out of sample or a holdout, or describes a later role as blind to these sources | That claim | None: every SM2 source is an exposed target (§1) |
| `FRAME_ATTRIBUTE_MISSING` | A frame that would use SM2's coefficients lacks a dimension's column; the Microcosm frame lacks education (design §7.2) | Use of the coefficients on that frame; closed-cohort work continues, labeled | None. The reference population's missing lifetime earnings is a declared proxy (§6.2), not this condition |
| `SMALL_CELL_DISCLOSURE` | A published aggregate from NHIS or ACS microdata rests on fewer than 100 unweighted persons, or a published death-based cell on fewer than 20 deaths (§11.5) | Publication of that artifact until the writer suppresses the cell and any complement that reveals it | Suppression |
| `CELL_CONSERVATION_BROKEN` | SM1's cell log on `R_ref` at any knot shows an infeasible cell, or a feasible cell that does not conserve deaths | SM2's admission | None |
| `GATE_FAIL_OR_REGRESSION_FAIL` | A tier A check fails; a family member's point residual lies outside `±τ`; a knot's calibration fails to converge or converges to two solutions (§6.3); an invariant fails; an SM1 test regresses | SM2's admission and everything resting on it: SM3's registration on these coefficients and SM4's use of them. The fit publishes the result with no seed selection and no tolerance relief; a new attempt needs a new registered version and enters the lane's attempt ledger (design §8) | None |
| `WEAK_POWER_OR_VACUITY` | A family member is inconclusive (§9.5), which includes every OACT e65 member while OACT's random-variation component stays open (§9.3); or a report presents the contrast members' pass, which reproduces inputs by construction, as evidence that the gradients are right | The affected dimension's admission, and with it SM2's admission as a whole (§9.5); the claim | None. SM2 makes no 0.90-power claim (S0.1 §2.5). The fit still publishes every residual, bound and dimension status |

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
   estimator of §4.5 and the Rao–Wu bootstrap of §9.3. It emits suppressed
   aggregates only (§11.4, §11.5).
5. **`reference_population.py`.** The ACS reader, the crosswalks, `Q̃`, the
   ordered logit and `R_ref(t)` with its replicates (§6.2), as suppressed
   aggregates.
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
| `quantity` | One of `rmr`, `death_rate`, `qx`, `rate_per_100000`, `deaths`, `population`, `standard_error`, `odds_ratio`, `z_statistic`, `mortality_ratio` |
| `printed_string`, `value`, `decimals`, `half_width` | The string as printed, its parsed value, its printed decimals and its printing (or digitization) half-width |
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
| ACS 1-year PUMS person files and data dictionaries, 2010–2024 | The Census Bureau's PUMS directory, https://www2.census.gov/programs-surveys/acs/data/pums/ followed by `<year>/1-Year/` | **Not checked**: census.gov lay outside this job's fetch scope. The fit job confirms each URL and records sizes and hashes before use |
| TR 2026 death probabilities | Already in the repository behind `data/tr2026.death_probability` (S0.1 §1.1) | — |

### 11.7 Invariants for property-based tests (Hypothesis, invented data)

- Printing intervals contain the printed point, widen as the half-width
  grows, and swapping the two values negates the interval.
- `q = m / (1 + m/2)` and `q = 1 − exp(−μ)` increase, stay in `[0, 1)`
  and invert exactly.
- Every completed table holds each category, sex and age 0–120 exactly
  once, with zero reference coefficients, and §5's rules reproduce the held
  values exactly.
- **Calibration round trip:** invented coefficients and an invented
  reference population generate targets, and §6.3 recovers the
  coefficients within `1 × 10⁻⁹`. With `λ = 0` and one dimension varying,
  JR-C equals JR-A. Permuting rows, or scaling every weight by one
  constant, changes no coefficient.
- Each calibrated table passes `RelativeRiskSpec` and SM1's cell
  conservation on the invented population.
- When the invented population's attributes are independent, its
  quintiles hold one fifth each and nothing caps, the fitted and target
  e65 agree exactly; the fitted life tables satisfy `life_table.py`'s
  invariants.
- **NHIS implied value under proportional hazards (M-H1):** when every
  category's hazard at each age of a band equals a fixed multiple of the
  reference category's, the age-standardized implied value of §4 equals
  the log of that multiple for any positive weights `W` and any age mixes
  of the two categories. A companion example with invented values shows
  the crude ratio failing the same check when the age mixes differ.
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
- `period_life_table` against `life_expectancy` for every fitted table.
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

The job read each with `sed -n 'a,bp'` in parts of at most 60 lines, every
part shown in full, and opened no harness-saved copy of any of them.

| File | SHA-256 | Parts |
|---|---|---|
| `EV/RESTRICTED-FILES.md` | `b09a2a56533b6880dd832135a60d315e171fa6850079940d8c1aee795f1a6351` | 13 (lines 1–742) |
| `EV/coordinator/restricted-files-pending-20261024.md` | `4b4936f05955541d4ad8b09ecf35ff01d73df104b01ae06c3446122e815ab931` | 2 (1–105) |
| `EV/coordinator/restricted-files-pending-20261025.md` | `9f78e02177b3591c58f7177179fdcb018d4daedf64b909e6dd6824e03e5972ac` | 1 (1–23) |
| `EV/coordinator/restricted-files-pending-20261025b.md` | `0fb8ba87bd8098062b3a133a2e501c0394ac34716e8ee93f1fb749baabf35a69` | 1 (1–38) |
| `EV/coordinator/restricted-files-pending-20261025c.md` | `8268e05c8f2e885aa114eb08391db13dc13ea78be503a582b015fda88738774b` | 2 (1–121) |
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
| `cbo_wp2007-11_cristia.txt` | `199af4eab22c9313bb7cc4e1b4981de7357b93b66b3e3d07a75675e8b7247c46` | Printed pp. 6–12, 14, 18–19 masked; Tables 1, 3, 5, 6 and Figure 2 layouts masked |
| `cbo_41681.pdf` | `e22720ad1ca203c5a801e61094c17a01d050b0c57ce929fa7dcb1d09573fb467` | Not opened |
| `cbo_41681.txt` | `f6d2891687ecb41ac06201e2c0fbd856fe126d0c4ce9376c257875a2cdc973af` | pp. 1–3, lines matching definitions and sources, masked |

"Masked" means a filter replaced decimals and comma-grouped counts before
display. Some integers still showed: page and year labels, a few
three-digit counts in Table 14's "not stated" row, and one three-digit
AIME breakpoint in Study 124's Table 2. None of them appears in this
record.

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
