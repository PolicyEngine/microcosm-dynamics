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
  population tables print each estimate with its standard error. The
  2018 and 2020 layouts were read with values masked; 2021 and 2022 come
  from the report text.
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
  2010–2024, with person weights and the 80 replicate weights. The 2020
  file carries experimental weights and is used and labeled as such. §6
  defines the population built from them. No ACS file was opened in this
  job, and their URLs were not checked here (§11.6).
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
