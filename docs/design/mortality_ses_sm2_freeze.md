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
  the fitted relative risks reproduce the targets they were fitted to,
  never that the model predicts. SM2 claims **no prospective prediction
  origin and no unused holdout** (S0.1 section 2.4). The held-out test of
  the gradient is SM3.
- **Authority.** Max approved the lane design, with its methodology, on
  23 October 2026 (decision d1922). S0.1's audit
  (`docs/design/s0_1_source_audit.md`, #588, merged 1 November 2026) is
  this record's input; its section 2 is SM2's record. Its header says a
  review and the gate's registration "confirm or amend" each
  **[proposed]** item before any outcome is computed, and "may tighten or
  rescope it but never loosen it". This record tightens or rescopes in
  the places section 2's table names, and loosens nothing.
- **Rulings that bind this record, unamended.**
  - **Q4:** relative risks are normalized within each single age × sex ×
    year cell to the baseline's expected deaths (SM1's normalizer,
    `src/populace_dynamics/mortality_ses/normalizer.py:328–382`).
  - **Q5:** lifetime earnings is the primary dimension; education and race
    and Hispanic origin are further dimensions of the same model.
  - **Q6:** the gradient holds at its last observed level as the primary
    path; a widening path is a registered alternative.
  - **Q11:** SM owns death alignment.
- **What it computes.** Nothing. This record states no fitted
  coefficient, no contrast between categories, no life expectancy and no
  comparison between sources' gradients, and it prints no source table
  value. It names tables, pages, age bands, years and categories only.
  Every number in it is a year, an age, a page, a count of table cells or
  targets, a code from a codebook, a tolerance the design or S0.1 sets, or
  a rule this record sets.
- **Data.** No PSID, HRS, SIPP or NHIS microdata file was opened, and
  nothing was computed on real data. PSID use follows the project's
  data-access record. DYNASIM, Urban Institute and PWBM material is not
  used or compared; it reaches these gates only through a validation lane
  (S0.1 scope). CBO publication 49659 stays closed; its methods count as
  open until a validation lane supplies a bounded definitions-only
  extract.
- **Markers.** **[frozen here]** marks a decision this record makes.
  **[frozen, S0.1 §x]** keeps a decision S0.1 already froze, with its
  pointer. **[open]** marks an item this record leaves unsettled and names
  what settles it. **[for Max]** marks a call section 12 sends up.

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
| S2-01 | 424 | **[proposed]** mapping assumption: OACT rate ratios used directly as annual-q multipliers, reported with the dynamic-AIME versus frozen-rank distinction and the beneficiary population difference | Confirmed and tightened: adds Study 129's exposure convention (deaths get a full year of exposure, so the published rates are initial-exposure probabilities, p. 5 and Appendix B pp. 13–14), the age-basis mapping, and three named mapping assumptions (M-E2 to M-E4) that every report carries | §4.1 | frozen here |
| S2-02 | 440 | **[open]** availability of earlier NCHS education editions | Settled by the NVSR listing and twelve earlier *Deaths: Final Data* reports: 2010–2017 cover reporting states only (31 rising to 49 states plus DC); 2018–2020 are national in the internet tables I–7 and I–19; 2021–2022 are national in printed Table 14 and Table VIII; no edition for 2023 is listed on 1 November 2026. The fit uses 2018–2022; 2010–2017 form a labeled sensitivity | §3.2 | frozen here |
| S2-03 | 474 | **[open]** harmonization of earlier NHIS years | Rescoped to NHIS 2009–2018 sample adults. The 2009, 2016 and 2018 layouts carry `EDUC1`, `HISPAN_I`, `RACERPI2`, `AGE_P`, `SEX`, `SRVY_YR`, `INTV_QRT` and `HHX`/`FMX`/`FPX` with identical code lists; the design variables are `STRAT_P`/`PSU_P` in 2009 and `PSTRAT`/`PPSU` in 2016 and 2018. The fit job checks each intervening year's layout against these names before use | §3.4 | frozen here (window and variables); intervening layouts checked by the fit job |
| S2-04 | 481 | **[open]** a three-dimension joint gradient conditional on lifetime earnings | Resolved by the joint route: joint marginal calibration on a public reference population, with the earnings–education–race dependence taken from a stated proxy. The dependence itself stays unidentified in public data, and §6.4 says so | §6 | frozen here (route); the dependence stays unidentified and named |
| S2-05 | 511 | **[open mapping]** Cristia's odds ratios | Frozen: predicted probabilities on a named reference population, then ratios to `q3`'s probability. Cristia enters only as a sensitivity and a source reported beside the fit; no log odds ratio enters as a log relative risk | §4.4 | frozen here |
| S2-06 | 520 | **[proposed]** CBO 41681 as context only | Confirmed. It supplies the reason the widening alternative leaves race and Hispanic origin flat (pp. 1–2) and no coefficient or target | §3.1, §7.4 | frozen here |
| S2-07 | 538 | **[proposed schema]** dimensions, columns, categories, references and unclassified treatment | Confirmed against `mortality_ses/specification.py`; tightened to one unclassified string per dimension, a fixed category order, and a crosswalk per source | §8 | frozen here |
| S2-08 | 564 | **[proposed loader]** OACT contrasts `log(r_q) − log(r_q3)`, band expansion, a source-year matrix that says what happens before a band first appears | Confirmed; tightened with the band-backcast rule, the figure-year rule and two independent table transcriptions | §3.1, §4.1, §5 | frozen here |
| S2-09 | 570 | **[open]** earnings ages below 62 and 90–120 | Frozen: the 62–64 coefficient holds down to age 25 and the age-25 value below; the 85–89 coefficient holds up to 120; three registered sensitivities | §5 | frozen here |
| S2-10 | 579 | **[open]** terminal 100+ rule and any unsupported other-group coefficient | Frozen: race contrasts at 100–120 hold the age-99 contrast, and the 100+ interval is not read as a contrast; `other_non_hispanic` comes from NHIS–LMF, with NCHS's AIAN and Asian tables reported beside as a partial group | §4.3, §5 | frozen here |
| S2-11 | 587 | **[open]** extraction and digitization of the 2022 gradient, its uncertainty, complete coverage | Frozen: vector extraction of Study 129 Figures 7–12, validated against Tables 7–12 at every table year, with a digitization half-width the validation sets; complete tables at every knot | §7.1–7.3 | frozen here |
| S2-12 | 591 | **[open]** widening `CoefficientPath`: slope, origin, ages, caps; knot years and synchronization | Frozen: origin 2024, slopes from a frozen estimator on OACT's pre-pandemic annual figures, caps of 30 years and a 1.5 multiplier, race held flat; annual knots 2010–2024 with one synchronization rule | §7.4–7.5 | frozen here |
| S2-13 | 602 | **[proposed]** `unclassified_rule="reference"` for SM3's overall denominator | Confirmed for SM3; `refuse` for conformance runs and for any projection until the frame carries the attributes | §8.3 | frozen here |
| S2-14 | 606 | **[open: identification]** marginal contrasts do not determine mutually adjusted coefficients; freeze a joint route and its reference distribution | Five candidate routes and one unavailable route; primary JR-C; JR-A (plain addition, labeled), JR-B, JR-D and JR-E as sensitivities | §6 | frozen here |
| S2-15 | 629 | **[open]** exact release dates of any earlier NHIS cohort used | Left open. The linked-mortality `.dat` files carry the listing date 26 April 2022; each NHIS year's release date settles from that year's survey description, which the fit job records. Nothing in SM2 depends on it, because SM2 claims no prospective origin | §3.4 | left open; settled by the fit job's per-year release ledger |
| S2-16 | 641 | **[frozen tolerance; proposed operationalization]** e65 target from source ratios on one baseline, with a fixed reference population, marginalization and tail rule | Frozen; the 0.1-year limit stays | §9.2 | frozen here (operationalization); tolerance frozen, S0.1 §2.5 |
| S2-17 | 649 | **[open]** whether the different source populations and baselines can satisfy the targets together | The procedure is frozen: one joint calibration per knot on one reference population, and a named failure when it cannot reproduce every target. Whether it can is an outcome, so this record does not settle it | §6.3, §9 | left open; settled by the fit under §9's rule |
| S2-18 | 659 | **[open until the loader plan is frozen]** the critical family's integer size and which joint-survey targets it holds | Frozen: **6,884** targets, itemized | §9.4 | frozen here |
| S2-19 | 677 | **[proposed named procedure]** `SM2_SOURCE_RECONSTRUCTION_AND_CLUSTER_BOOTSTRAP` | Filled in step by step | §9 | frozen here |
| S2-20 | 688 | **[proposed suppression]** at least 100 unweighted persons per published microdata subgroup | Confirmed and tightened: also at least 20 deaths in any published death-based cell, and the rule applies to ACS as well as NHIS aggregates | §11.5 | frozen here |
| S2-21 | 353 | Unmarked: CBO 49659's "safely bounded definitions remain open" | Left open as the brief requires; SM2 uses no part of 49659 | §3.1 | left open; settled by a validation lane's definitions-only extract |
| S2-22 | 523 | Unmarked: "CBO 49659's mixed-source methods remain open pending a safely bounded definitions-only extract" | Same item as S2-21 | §3.1 | left open; as S2-21 |
| S2-23 | 588 | Unmarked: "A 2020 table-only path is a proposed registered sensitivity" | Confirmed as sensitivity P-TABLE; it cannot become primary without amending Q6 | §7.3 | frozen here |
| S2-24 | 669 | Unmarked: a source that does not publish the uncertainty a target needs leaves that item "open or inconclusive" | Applied: OACT publishes no deaths or exposures, so OACT's random-variation component stays open, with the consequences §9.3 states | §9.3 | left open; settled by OACT exposure or death counts by sex × band × quintile × year |
| S2-25 | 698 | Unmarked: "`SOURCE_UNAVAILABLE` / open identification applies to the complete modern three-dimension joint source and missing source-age mappings" | Each trigger and fallback stated | §10 | frozen here |

**Counts.** Of the 25 rows, 20 are frozen here, 5 are left open with what
settles them (S2-15, S2-17, S2-21, S2-22, S2-24), and none goes to Max as
a row. S2-03 is frozen with a check the fit job performs. Section 12 holds
the two calls that go to Max; neither comes from a row of this table.

## 3. Source-year matrix

Every source below was read in this job at the SHA-256 that section 13
lists. "Fit" means the source supplies a target the joint calibration
reproduces; "beside" means the source is reported beside the fit and is
not fitted; "context" means it informs a reason and supplies no number;
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
| Cristia (2007), CBO Working Paper 2007-11 | Tables 3–4, age-standardized mortality ratios, PDF pp. 38–39; Tables 5–6, logistic regressions, PDF pp. 40–41 | Lifetime-earnings quintiles (own and household); race and ethnicity; education; marital status | Men (Tables 3, 5), women (Tables 4, 6) | 35–75, 35–49, 50–64, 65–75 | Person-years 1983–2003 | Beside, and sensitivities JR-D (§6) and T-E3 (§5) |
| CBO publication 41681 (17 April 2008) | pp. 1–3, Figures 1–2 | Synthesis | — | — | — | Context (§7.4 reason) |
| CBO publication 49659 (7 November 2014) | — | — | — | — | — | Closed; methods open until a validation lane supplies a bounded definitions-only extract |
| OACT presentation, Tiffany Bosley, 14 January 2025 | Slides 1, 3, 23 | — | — | — | — | Identity of the January 2025 update only (S0.1 §2.1) |

**Bands and years in Study 129.** Each table prints "-" in a band whose
cohorts are not yet all in the study, which takes only workers reaching
62 in 1993 or later (notes under Tables 1–12). A band `[a1, a2]` is fully
supported from year `1993 + (a2 − 62)`: 62–64 from 1995, 65–69 from 2000,
70–74 from 2005, 75–79 from 2010, 80–84 from 2015 and 85–89 from 2020.
The printed tables match that schedule. Study 124's Tables 4–8 follow the
same schedule through 80–84 in 2015.

**Printing.** Tables 7–12 print RMRs to two decimals and the share row to
one decimal; Tables 1–6 print rates to four decimals (counted from the
text layer without reading values: 252 two-decimal and 252 four-decimal
quintile-or-total cells, which equals 21 band-years × 2 sexes × 6 rows).

**Figures as vector content.** Page 34's content stream holds 1,281
line-to and 846 move-to operators and no raster plot image; pages 34–38
list no image object at all, and page 33 lists only 14 small 16 × 16
stencils and one ccitt strip (`pdfimages -list`). The annual series can
therefore be recovered from path coordinates (§7.2).

**Appendix lettering.** The body text places Tables 7–12 in Appendix E
and Figures 7–12 in Appendix F (pp. 7, 9), but the printed headings read
"D. Age Group Death Rate Figures" (p. 21) and "E. Age Group Relative
Mortality Ratios by AIME Quintile Levels" above Figure 7 (p. 33), and
Tables 7–12 carry no letter (p. 27). This record cites tables and figures
by number and page only.

**Before a band first appears.** For a knot year earlier than a band's
first fully supported year, the band's targets take their values from that
first year (`BAND_BACKCAST_HOLD_FIRST`): 80–84 for 2010–2014 from 2015,
and 85–89 for 2010–2019 from 2020. These copies are assumptions, not
published values; they enter no critical-family count as new targets
(§9.4), and §5 names the alternative. A figure point plotted in a year
before its band is fully supported is recorded and never fitted.

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
  older ages"); data "about 97% complete" (NVSR 74(4) p. 127). The
  denominators come from 1-year ACS PUMS adjusted to July 1 resident
  control totals (p. 132), and the rates' standard errors combine Poisson
  variation in deaths with the ACS standard error (Formulas 9 and 10,
  p. 132). The 2020 denominators use the 2020 1-year ACS PUMS (NVSR 72(10)
  internet tables, p. 2).
- **No later edition.** The NVSR listing fetched on 1 November 2026 holds
  no *Deaths: Final Data for 2023*; its latest final-deaths report is NVSR
  74(4) for 2022. The last observed education year is therefore 2022.
- **Why 2010–2017 are not fitted.** Their populations are the reporting
  states, not the United States, so their denominators and composition
  differ from the reference population (§6). The 2010–2017 category set
  and age bands were not checked in this job; sensitivity E-S1's loader
  checks them before use.
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
  the total, NH black and NH white tables only, and old-age mortality for
  the Hispanic, AIAN and Asian NH tables is modeled (pp. 2, 54–55); the
  2008-onward method smooths death rates above about 85, at ages that
  depend on the group (p. 53).
- **Fit.** Hispanic, NH white and NH black for every knot year 2010–2024
  (bridged race through 2017, single race from 2018, both labeled). The
  2006–2009 tables lie before the first knot and are not used.
- **The `other_non_hispanic` group.** No NCHS table covers it. AIAN and
  Asian NH tables leave out Native Hawaiian and Pacific Islander,
  multiracial and other people, and exist only from 2019, so a weighted
  average of them is not the full group (S0.1 §2.3). The fit takes this
  group's contrast from NHIS–LMF (§3.4); the AIAN-and-Asian composite for
  2019–2024 is reported beside it, labeled "partial group".

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
  flags that show whether race or ethnicity was imputed (2018 survey
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
  defines the population built from these files. No ACS file or ACS
  documentation was opened in this job, and their URLs were not checked
  here (§11.6).
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
`mortality_ses/model.py:171–184`).

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
  single year of age and cuts quintiles there (pp. 3–4), so survivors are
  ranked anew at every age; the study notes that people in high quintiles
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
  pools SM's `some_college` and `college`. Its target is matched by the
  model's pooled `q` over both categories, weighted by the reference
  population, so NCHS identifies one combination of the two coefficients.
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
  definitions (§8.2), and the 2017–2018 break is labeled in every path.
- **M-R6, ratios to the total population.** For the e65 target only
  (§9.2), each group's `q` is divided by the NCHS total-population `q` at
  the same age and year.
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
  observation years), with equal quintile shares. The ranges are 35–49,
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
- **Attained age.** `AGE_P` plus elapsed time. Because birth dates are
  suppressed, each person-year is split across attained ages on the
  assumption that birthdays fall uniformly through the year. A person
  with `AGE_P = 85` (85 or older at interview) contributes only to the
  85+ band, whose lower bound is then known.
- **Model.** For each sex, band and dimension, a survey-weighted Poisson
  regression of deaths on that dimension's category indicators and
  single-year attained-age indicators, with log person-years as offset.
  The exponentiated category coefficients are the marginal hazard
  ratios.
- **Missing values.** `EDUC1` 97–99, `HISPAN_I` 11 and any race code that
  §8.2 leaves unclassified drop out of that dimension's estimate only;
  their counts are reported.
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
| Race and Hispanic origin: `hispanic`, `black_non_hispanic` | Single ages 0–99 | None needed | `TAIL_R_HOLD_99_UP`: ages 100–120 take the age-99 coefficient; the "100 and older" interval is not read as a contrast | T-R1: a taper from the age-99 value to zero at age 110, labeled as T-E3 |
| `other_non_hispanic` | 25–44, 45–64, 65–74, 75–84, 85+ (NHIS–LMF) | `TAIL_O_HOLD_25_DOWN`: ages 0–24 take the 25–44 coefficient | 85+ runs to 120 | T-R2: for 2019–2024, the partial AIAN-and-Asian composite (M-R4) replaces NHIS at every age, labeled "partial group" |

- **T-E2, Cristia's age shape.** For each sex and non-reference quintile
  `k`, let `c_b(k)` be Cristia's marginal log contrast against `q3` in age
  range `b` (M-C2). Ages 50–61 take the 62–64 coefficient times
  `c_50–64(k) / c_65–75(k)`, and ages 25–49 times
  `c_35–49(k) / c_65–75(k)`. A ratio is replaced by the pooled
  least-squares slope over the four quintiles when `|z| < 2` for the
  quintile's 65–75 odds ratio, and every ratio is bounded to `[0.5, 3]`;
  both guards are fixed here to keep a ratio of small numbers from
  driving the sensitivity.
- **Ages under 25.** Lifetime earnings and completed education are not
  yet formed for most people under 25, and SM3's population starts at 50.
  The held values below 25 exist because SM1's table must be complete; a
  frame that classifies a person under 25 on either dimension must
  register that use first (§8.3).
- **The baseline's top.** Ages 100–120 multiply a baseline `q` that is
  already large, and SM1 caps each probability at one and conserves the
  cell's deaths by recomputing the factor over the uncapped rows
  (`normalizer.py:338–356`). Capped cells are logged, and §9.1 checks the
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
Correlation can make the sum overshoot or undershoot, and its direction
depends on the joint distribution; it is not known in advance (S0.1
§2.3). Turning marginal targets into conditional coefficients needs a
**reference joint distribution** of the three attributes by sex and single
age, and an assumption that the effects add on the log scale.

### 6.2 The reference population `R_ref(t)` [frozen here]

For each knot year `t` (2010–2024), `R_ref(t)` is the weighted ACS 1-year
PUMS population of that year: every person record the file holds,
including group-quarters records where the file carries them (the fit job
records which it does), with these attributes:

- **Sex and single age.** Ages at or above the year's top code (read from
  that year's data dictionary) share the top-coded group's composition.
- **Education and race and Hispanic origin.** From the ACS education,
  Hispanic-origin and race items through the crosswalk in §8.2.
- **A lifetime-earnings quintile proxy `Q̃`.** At ages 62–89, among
  persons with positive Social Security income, `Q̃` is the weighted
  quintile of that income within sex and single age; weight that straddles
  a quintile boundary is split so each quintile holds exactly one fifth.
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
  logit with cut points `c_k(s, a, t)` recomputed so that every quintile
  holds exactly one fifth of the full population at that age. OACT
  targets are evaluated on the subpopulation with positive Social
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
ages outside these blocks follow §5. Each target's implied value is
computed by expanding `R_ref(t)` into rows, one per (quintile, education,
race) combination at each single age, with weight `w`, applying the
candidate coefficients and SM1's `normalize_probabilities` cell by cell
against the baseline `q`, and averaging the normalized probabilities over
the target's ages and subpopulation (§4, common scale).

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
| **JR-D: Cristia-bridged shrinkage** | The 1983–2003 ratio of mutually adjusted to marginal contrasts in SIPP–SSA data at 35–75, carried to modern marginals | None named; it is implicit in Cristia's sample | Cristia's Tables 3–6 | Nothing | The ratio may not carry across two to four decades and a different population; columns 2, 4, 6 also adjust for marital status; rounded z statistics; it reproduces no modern marginal on any named population, so no e65 can be checked |
| **JR-E: NHIS direct joint model** | Education and race hazard ratios adjusted for each other in NHIS's 2009–2019 population; earnings as JR-B | The NHIS sample itself | NHIS–LMF | Supplies everything for education × race at attained ages 25+; cannot supply earnings, single ages above 84 at interview, or deaths after 2019 | Does not reproduce NCHS's targets (different population, years and reporting); survey precision; the earnings overlap as JR-B |
| **JR-F: PSID reference population (not available)** | As JR-C, with the deployment population's own joint distribution | The PSID cohort's lifetime-earnings × education × race distribution | — | — | PSID use follows the project's data-access record. This record does not use it; §12 sends the underlying principle to Max |

**JR-D's definition [frozen here].** For dimension `X`, sex `s` and
Cristia age range `b`, `κ_X(s, b)` is the weighted least-squares slope,
through the origin, of Cristia's conditional log contrasts (M-C3) on its
marginal log contrasts (M-C2 for earnings, M-C5 for education and race),
across the dimension's non-reference categories, with weights equal to
the categories' shares in Cristia's Table 1 where it prints them and
equal weights otherwise; `κ` is bounded to `[0, 1]`. JR-D's coefficients
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
