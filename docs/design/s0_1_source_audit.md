# S0.1: source, exposure, access and power audit for SM2, SM3, SM4, ED1 and ED2

*Frozen record, 24 October 2026, for blinded review. Branch
`mgf-s0-1-source-audit-20261024`.*

- **Authority.** The mortality, groups and financing design (#558),
  approved with its methodology on 23 October 2026 (decision d1922) at
  commit `2c19f5b6856b9da62924706067ef96f00f55012d`. Its section 5.2 lists
  what S0 freezes, section 5.3 proposes the limits, section 8 names the
  conditions and kill criteria, and section 11 records the lane's
  exposure. S0.1 follows SM1 (#570) on lane M.
- **Rulings that bind this record.** Relative risks are normalized within
  each age × sex × year cell (Q4). Lifetime earnings is the primary
  dimension, with education and race and Hispanic origin as further
  dimensions (Q5). The gradient holds at its last observed level as the
  primary path, with a widening path as the registered alternative (Q6).
  Whether to authorize SM3's real-PSID step is decided at S0.1, once its
  power is known (Q7). The final section is the input to that decision; this
  record makes no recommendation on it.
- **Scope.** The gates SM3, SM2, SM4, ED1 and ED2, in that order. The group
  gates GR1–GR4 are audited separately, by a lane unexposed to published
  group results. PWBM's sources are located at S0.2. Urban Institute and
  DYNASIM material reaches these gates only through a validation lane, as
  a labels-only or definitions-only extract.
- **Data.** No PSID or HRS data was opened, and no PSID statistic was
  computed. PSID use follows the project's data-access record. Every power
  figure comes from invented populations (`scripts/s0_1_power.py`, results
  in `docs/design/s0_1_power_results.json`) or from public documentation.
- **Markers.** **[frozen]** is a fact read at the locator given, or a rule
  the design already fixes; it changes only by a recorded amendment.
  **[proposed]** is a choice this audit makes; the blinded review and the
  gate's registration confirm or amend it before any outcome is computed,
  and may tighten or rescope it but never loosen it. **[open]** is
  unsettled; the item names what settles it.
- **Sources.** Download retrieval dates are 24 October 2026 unless an older repository
  capture is identified; raw bytes still to retrieve are explicitly open. Each
  URL, size and full SHA-256 are in the source manifest
  (`EV/mortality-groups-financing-20261021/s0_1-sources/MANIFEST.md`, moved
  from this job's untracked `.s0_1-sources/`). The tables below repeat the
  SHA-256 of every source a gate depends on. Repository paths are at
  `origin/master` `2195258c` unless a commit is given.

## Scope and status

All five records below distinguish established source/code facts from
proposed test choices and open feasibility items. No empirical gate is
admitted by this audit. SM3's shipped attribute construction requires a
retrospective conditional label; actual counts and unused holdout
provenance remain open. SM2 remains calibrated, not validated. SM4 is
report-only. ED2 waits for starting education and a dated unused target.

## 1. SM3: the mortality-gradient gate

### 1.1 Sources, population and estimand

**[frozen]** SM3's intended population is the closed PSID 2010 cohort,
observed in the 2011 wave, born in 1980 or earlier, with the 2011
core/immigrant cross-sectional weight `ER34155`
(`src/populace_dynamics/cohorts/psid2010.py:1–25, 235–270`). PSID use
follows the project's data-access record. No file in that population was
opened for this audit; staging and all file digests remain **[open]**.

| Input | Variables and exact role | Reference/interview/availability | Status |
|---|---|---|---|
| Cross-year `IND2023ER` (`data/psid.py:68–77`) | `ER30001`, `ER30002` identify persons; `ER32000` sex (1 male, 2 female, 9 NA); `ER32050` year of death, with exact years 1967–2023, packed `AABB` two-digit-year ranges, 0 not known deceased and 9999 year unknown (`data/deaths.py:85–115`). No death month is available | Death information through 2023; historical wave reports in a later release; exact release/revision dates not established | [open: release dates and staged digest] |
| 2011 anchor (`cohorts/psid2010.py:235–270`) | `ER34101` interview; `ER34102` sequence; `ER34103` relation; `ER34104` age; `ER34106` reported birth year; `ER34155` weight | Status/interview in 2011, income reference year 2010; public release date open | [frozen: code definitions; open: availability] |
| Family reports (`data/group_attributes_psid.py:124–138`) | Head/spouse race and Hispanic origin, 1985–2023; completed education from individual-wave reports for members aged 16+; historical head/spouse labor income | Annual interviews through 1997 and biennial thereafter; income ordinarily preceding interview; edition-specific release dates open | [frozen: reader windows; open: dates] |
| Survey design (`cohorts/age67.py:314–315`) | `ER31996` sampling-error stratum; `ER31997` cluster; family identifiers must remain nested within the survey design when resampling | Later cross-year release; release dates open | [proposed: design estimator] |
| Baseline (`baselines/tr2026_intermediate.py:135–159`) | OACT TR 2026 single-age, sex, year `q`, via `data/tr2026.death_probability`; historical through 2023 then Alternative II | Published 9 June 2026; captured 1 October 2026 (`data/external/tr2026/provenance.md:109–112`) | [frozen: permitted baseline; not available before 2011] |
| Gradient | SM2 coefficient tables consumed by SM1, pinned with their reference population, path and source digests | Study 129 reference years 1995–2022, December 2024 publication; other SM2 dates in section 2 | [open: SM2 build] |

**[proposed] Estimand.** For each dimension `d`, category `g`, sex and
age band `s`, let `O_gs` and `E_gs` be weighted observed and expected
deaths. Register

`R_gs = (O_gs / E_gs) / (O_all / E_all)`.

The denominator is the **analytic cohort's overall ratio over all
registered sex and age-band person-years**, shared by all cells. This
proposed scope keeps the m6 attrition-confounded 85+ risk set out of both
the critical cells and their denominator, and must be named explicitly in
the registration. It is not a separate
sex/band ratio. Persons unclassified on dimension `d` enter the overall
numerator and denominator and no cell of `d`. Its covariance with every
cell belongs in the variance estimator. Changing the baseline's pattern
across age and year can change `R`; division by the overall ratio does
not cancel that pattern.

**[proposed] Window and risk sets.** Calendar 2011–2023, single-year
start-of-year ages `year − 1 − birth_year`, within 50–64 and 65–84.
Persons may contribute to both bands over time but may die only once;
resampling must retain their entire histories. Unknown baseline sex or birth year requires a registered
risk-set/expected-death rule; it cannot disappear silently from the overall
accounting. An interview-selected 2011 cohort is left truncated during 2011. **[open]** Registration must
settle interview-date availability and partial-year risk exposure before
using 2011; a 2012–2023 window is a proposed sensitivity, not a silently
changed primary. Exact-year, interval-censored, unknown-year deaths and
attrition require a registered risk-set rule. The floors builder's
half-year-of-death convention (`scripts/build_mortality_floors.py:35–62`)
is a candidate, not proof that missing deaths are ignorable. Every
excluded/unknown class remains in the disclosure-controlled accounting.

**[frozen repository baseline pins]** OACT's 2026 single-age `q`
source captures are dated 1 October 2026. Their official download URLs,
bytes and hashes are in `data/external/tr2026/provenance.md:109–112` and
repeated in the source manifest. Female Alt2:
`e3178487512f23666ca05754246798557275bc0728f3f937bbca97358f32532b`;
female historical:
`1e2ecd7d24233310108da582ae922c53205d1d239ce3a484ecc5fd6cdb88d0c8`;
male Alt2:
`4e2a632a964fadb4cc3fe6127a97ef656eafd43348bf8c7408b018b83840db27`;
male historical:
`ee423873ef2b532fc53c97312a9d6162b876f56e50bd227d45f6c9d9a1cefc8f`.
The coefficient loader must preserve SM1's single-age convention, cap at
120 consistently, and register its open-interval closing rule; the
baseline repeats age 119 at 120 (`baselines/tr2026_intermediate.py:154`).

### 1.2 Prediction origin and group attributes

**[frozen finding] The shipped construction cannot establish attributes
available before 2011.** `cohorts/group_attributes.py:15–25` explicitly
resolves race and Hispanic origin using every head/spouse report
1985–2023. `build_group_attributes` calls `_resolve_race` without a wave
cutoff (`:1004–1021`), even though education has an anchor-wave cutoff.
Both classification and missingness can depend on later reports and on
survival to those reports. The cohort builder also uses 2011 interviews
to define membership. Historical interviews inside a later release do not
establish that the values, weights or revisions were available before
2011.

**[proposed settlement] With existing inputs, SM3 must register as a
retrospective conditional analysis.** No time-prospective admission is
claimed. A new boundary-filtered loader is technically possible: filter
before provenance sealing, enforce a pre-2011 cutoff on every report and
birth-year source, and use an independently frozen population. The
2009-anchor alternative (`cohorts/psid2010.py:14–25`) is a candidate.
It remains **[open]** until the loader, original release availability,
cohort membership, revisions and all imputation donors are audited. This
source audit does not implement it or certify its feasibility.

**[proposed] Lifetime-earnings quintiles.** Use own head/spouse labor
income at ages 22–61 through the registered cutoff, AWI indexed to one
frozen year, capped at each income year's taxable maximum, zeros counted,
and average over the registered observed/imputed years. Cut weighted
quintiles within sex × five-year birth cohort, with a deterministic tie
rule frozen before counting deaths. Require ten observed head/spouse years;
otherwise unclassified. This is a partial-career proxy, not OACT's
highest-35-year AIME. The same crosswalk must label SM2 and SM3.

The existing career builder uses income years 1968–2010 and imputes odd
years 1997–2009 from neighboring years (`cohorts/psid2010.py:52–58`).
Its last income year uses the 2011 interview. A proposed pre-2011
alternative stops at income year 2008 from the 2009 wave; no 2010 donor
may fill 2009. **[open]** The index-year AWI, annual wage-base releases,
all family/individual release dates, early-career missingness, denominator
of the average, and ties require an exact dated input ledger. Completed
lifetime earnings that include future reports cannot be a baseline
covariate.

**[proposed] Categories and reference categories.** Lifetime earnings:
`q1`–`q5`, reference `q3`. Education: `less_than_high_school` (<12 years),
`high_school` (12, reference), `some_college` (13–15), `college` (16–17,
the reader's upper code). Race and Hispanic origin: `hispanic`,
`white_non_hispanic` (reference), `black_non_hispanic`,
`other_non_hispanic` (`cohorts/group_attributes.py:110–115`). Missing and
unresolved statuses are not a fifth race category or assigned a quintile.

### 1.3 Holdout partition and exposure history

**[frozen]** All SM2 reference/interview/publication dates must appear in
its registration: Study 124 (1995–2015, June 2017 MBR, April 2018
publication); Study 129 (1995–2022, June 2023 MBR, December 2024
publication, corrected figure June 2025); NCHS 2022 life tables
(8 April 2025); NCHS 2024 tables (25 August 2026); 2022 final deaths
(10 June 2025); NHIS interviews 1986–2018 with deaths through 2019,
public LMF documentation April–May 2022; Cristia (SIPP interviews
1984–2001, death follow-up through 2003, August 2007 publication).
These overlap or postdate SM3's window. The primary calibration cannot be
called available at a pre-2011 prediction origin.

**[frozen: exposure metadata only]** The following artifacts are already
on the exposure record; this continuation reads only raw-byte digests,
addition commits and top-level key names, never values:

| Artifact | SHA-256 | Addition commit | Top-level keys |
|---|---|---|---|
| `runs/mortality_floors_v1.json` | `24075adc58feb8360bade74ad33cbdce1a3ed004536dc3bb59471a7b3d9d28b7` | `421a5881d1ae35a1858b2b86810e3b22760e882b` | `age_bands`, `component`, `data`, `elapsed_seconds`, `exposure_construction`, `external_anchor`, `internal_noise_floor`, `proposed_thresholds_note`, `purpose`, `reported_anchor_not_gated`, `revision_pins`, `run`, `schema_version`, `sexes` |
| `runs/m6_holdout_floors_v3.json` | `e931c88622fad84e8f8b2cf18940cbe27da1c93e0d009dfbaa3d6c6cae050c77` | `1818784f88d533c2907e15a536f8d05e04476f3c` | `candidate_blind`, `cell_meta`, `coarsening_ladder`, `data`, `design_pins`, `earnings_decompounding_ladder`, `elapsed_seconds`, `f6_weight_rule`, `faithful_candidate_oc`, `floor`, `household_id_weight_carriage_rule`, `invariants_held_fixed`, `metric_caps`, `no_projection_no_candidate`, `oc_before_lock`, `partition`, `presence_conditioning`, `reported_truth_side_only`, `revision_pins`, `run`, `schema_version`, `split_units`, `split_width_diagnostic`, `supersedes_note`, `tolerances`, `v1_pause_evidence`, `v2_lineage` |

The mortality-floor builder/lane inspected PSID hazards by age band and
sex; m6's builders inspected mortality power surfaces. The design lane's
section 11 records its readings of the mortality artifact's keys/string
fields, public NCHS and CBO snippets, and its excluded DYNASIM/group
exposure. That exposure belongs to those sessions; this audit inherits
knowledge of its existence, not their comparator values.

**[frozen]** `gates.yaml:5393–5410` says m6 certifies nothing about
mortality drift, no admissible pooling of its 25–84 surface cleared its
cap, and its 85+ stratum was attrition-confounded. This is power history,
not a power calculation for SM3.

**[open: unused holdout]** No exhaustive exposure clearance is possible
from code and artifact key names. A metadata-only scan cannot establish
that deaths by earnings, education or race have never been inspected.
The preserved draft flagged a possible AIME/mortality artifact; an
outcome-aware validation role must settle that question without supplying
values to this lane. A separately documented unused outcome partition is
required before any claim of held-out prediction. Retrospective
conditional registration does not restore blindness to exposed outcomes.

### 1.4 Critical cells, bounds and pass conjunction

**[proposed]** Admit dimensions separately: five earnings quintiles × two
sexes × two age bands = 20 cells; four education categories × two × two =
16; four race/Hispanic-origin categories × two × two = 16. Register each
family before outcomes. Report the stricter 52-cell family as a
sensitivity; any joint 95% admission across all three dimensions requires
that joint family, rather than combining three marginal admissions; pooling sexes or bands is a separately registered rescoping,
not permission to choose a favorable partition after results.

**[frozen tolerance]** Every cell must satisfy
`|log R| ≤ log(1.15) = 0.1397619424`. The exact logarithm tightens the
design's rounded 0.14. A missing/suppressed cell never disappears from
the conjunction. A no-gradient model's implied `R` must be reported on
invented/reference inputs; a tolerance that cannot discriminate that
model triggers `WEAK_POWER_OR_VACUITY`.

**[proposed uncertainty]** Use simultaneous 95% two-sided bounds,
Bonferroni over the frozen family: `z = Φ⁻¹(1 − .05/(2m))`. Taylor
linearize the ratio of ratios including the shared denominator and full
person histories. Respect sampling-error strata, survey clusters and
family clusters with domain estimation over the full design, keeping
unclassified persons. Check using a Rao–Wu stratified cluster bootstrap;
use the wider supported interval if methods disagree. Singleton strata,
zero deaths and an unestimable design yield inconclusive cells.
Monte Carlo error of each reported bound must be < `log(1.15)/10`;
verify it using independent batches, not a fixed replicate count alone.

**[proposed conjunction]** A dimension passes only if every simultaneous
interval lies wholly within the tolerance. A wholly outside interval
fails; overlap, missingness or inadequate precision is inconclusive.
Insufficient precision is never a pass. Family power is the probability
of the entire pass conjunction at true `log R = 0`, not rejection power
against a zero-difference null. The named procedure is
`S01-Bonferroni-Equivalence-Grid-v2` in `scripts/s0_1_power.py`:
conservative family-power bounds over invented counts/rates and simulation
of complete families with their shared denominator. Section 6 gives the
assumptions and 0.90 thresholds; actual feasibility remains open.

### 1.5 Suppression and named conditions

**[frozen source; proposed stricter rule]** SSA's MINT8 Table User Guide,
“Sample Size Restrictions”, `#sample-size`, requires at least 100
individuals per row and whole-characteristic-subgroup suppression; its
percentage numerators must be zero or at least 10. Repository capture
`data/external/mint8_table_user_guide.source.html:518–523`, SHA-256
`8d5bc3f0de17831c2ed07383003257a63bb657df179d0c54868fda052f23f100`;
public locator https://www.ssa.gov/policy/docs/projections/user-guide.html#sample-size. This audit proposes
at least 100 unweighted persons and at least 10 observed deaths for an
SM3 published cell, whole dimension × sex × band suppression when a
category fails, and complementary suppression preventing subtraction.
Suppressed cells are inconclusive. No raw small-cell counts leave the
registered disclosure-controlled step.

- **`EXPOSURE_UNRESOLVED`: triggered** for any prospective/unused-holdout
  claim using the shipped inputs; prediction-boundary availability and
  previous by-group exposure remain open.
- **`WEAK_POWER_OR_VACUITY`: triggered on assumed grid rows** whose
  complete family cannot reach 0.90; no claim about actual PSID power
  follows without the separately registered structural counts.
- **`SOURCE_UNAVAILABLE`: open**, for staged-file digests, dated original
  releases and the joint-gradient input; no staging check was made.
- **`SMALL_CELL_DISCLOSURE`** stops publication of an unsuppressed small
  cell. **`GATE_FAIL_OR_REGRESSION_FAIL`** stops the affected admission.
  **`MORTALITY_CHANGE_UNADMITTED`** stops downstream use until all affected
  Track B change-admission checks pass. SM2 may also trigger
  **`GRADIENT_SOURCES_INCONSISTENT`**.

**[frozen kill criterion]** If S0.1 finds no source pair supporting a
held-out gradient test at 0.90 power on any dimension, SM3 is not
registered; the mortality-differences row remains *Built, ungated*,
“calibrated, not validated”. Two independently justified failed successors
pause the mechanism (design section 8). The present audit has not
established such a source pair: holdout provenance, joint mapping and
actual structural precision are open. Invented-data thresholds are a
decision input, not an empirical admission or an authorization decision.

## 2. SM2: gradient inputs and their calibration

**[frozen]** SM2 is external-target conformance, labeled “calibrated, not
validated”. It supplies SM1's coefficient specification. Q4 preserves
weighted baseline expected deaths within single-age × sex × year cells;
Q5 makes lifetime earnings primary, with education and race and Hispanic
origin further dimensions; Q6 holds the last observed gradient on the
primary path and registers widening as an alternative. No SM2 coefficient,
fit result or source-disagreement statistic has been computed here.

### 2.1 Sources and the January 2025 settlement

**[frozen]** All sources below were retrieved on 24 October 2026.
Sizes and full download URLs (including archival captures) are in the
manifest. These are calibration sources; CBO 49659 is mixed content whose
methods require a safely bounded definitions-only extract.

| Source | Publisher, vintage | URL | SHA-256 | Local file | Access date | Reliance |
|---|---|---|---|---|---|---|
| Actuarial Study No. 129, *Mortality by Career-Average Earnings Level* (Bosley) | SSA OACT, December 2024, figure 6 corrected June 2025 | https://www.ssa.gov/oact/NOTES/pdf_studies/study129.pdf | `937ec3b6c3109426ba8d87e0956e320bdc29ab6ffa07625ae1b379635d04e414` | `oact_study129.pdf` | 2026-10-24 retrieval; 2026-10-25 checksum | Primary earnings-gradient definitions; section 2.2 |
| Actuarial Study No. 124, same title (Bosley, Morris and Glenn) | SSA OACT, April 2018 | https://www.ssa.gov/OACT/NOTES/pdf_studies/study124.pdf | `ef66df96b8a21fe59bf4fef79aa48c950d3fff866e6725f4dd5c5f339f10ac38` | `oact_study124.pdf` | 2026-10-24 retrieval; 2026-10-25 checksum | Earlier methods and earnings crosswalk; sections 2.2 and 3.1 |
| *United States Life Tables, 2022*, NVSR 74(2) | NCHS, 8 April 2025 | https://www.cdc.gov/nchs/data/nvsr/nvsr74/nvsr74-02.pdf | `3312964360b9a33663be89248f7e75c39e99f895dd04ca86659115fe1a318421` | `nchs_nvsr74-02.pdf` | 2026-10-24 retrieval; 2026-10-25 checksum | Race/origin and sex life-table definitions; section 2.2 |
| *United States Life Tables, 2024*, NVSR 75(5) | NCHS, 25 August 2026 | https://www.cdc.gov/nchs/data/nvsr/nvsr75/nvsr75-05.pdf | `43e24a1f249f017fcc505a601eb5738f0797506e35b67c4722c91791777d8842` | `nchs_nvsr75-05.pdf` | 2026-10-24 retrieval; 2026-10-25 checksum | Later life-table vintage and definitions; section 2.2 |
| *Deaths: Final Data for 2022*, NVSR 74(4) | NCHS, 10 June 2025 | https://www.cdc.gov/nchs/data/nvsr/nvsr74/nvsr74-04.pdf | `bb7b356841b202cba6a845315679b42424945a78240414dbe67bd100d428b26b` | `nchs_nvsr74-04_deaths_final_2022.pdf` | 2026-10-24 retrieval; 2026-10-25 checksum | Education death-rate table scope; section 2.2 |
| *Public-use 2019 Linked Mortality File Description* | NCHS, May 2022 | https://www.cdc.gov/nchs/data/datalinkage/public-use-linked-mortality-file-description.pdf | `2e9cae2ffd17b276d200f9388860e682f995a7210bb004bdba54f63f412e446c` | `nchs_lmf_public-use-linked-mortality-file-description.pdf` | 2026-10-24 retrieval; 2026-10-25 checksum | Public linkage eligibility and censoring; section 2.2 |
| *Codebook for the 2019 Public-Use Linked Mortality Files* | NCHS, 28 April 2022 | https://www.cdc.gov/nchs/data/datalinkage/public-use-linked-mortality-files-data-dictionary.pdf | `5a62ebb5573030ce448756fc48f0618561d713aa4b48b9b1a2669ff20db7bbd6` | `nchs_lmf_public-use-linked-mortality-files-data-dictionary.pdf` | 2026-10-24 retrieval; 2026-10-25 checksum | Public mortality variables and definitions; section 2.2 |
| Linked Mortality Files page | NCHS, revised 7 July 2026 | https://www.cdc.gov/nchs/linked-data/mortality-files/ | `0d599231ec9d3450066a9d9537b9a83272746b87336c73e6ea45ca2e8aeb55c3` | `nchs_lmf_public.html` | 2026-10-24 retrieval; 2026-10-25 checksum | Public release identity and availability; section 2.2 |
| Cristia, *The Empirical Relationship Between Lifetime Earnings and Mortality*, Working Paper 2007-11 | CBO, August 2007 | https://www.cbo.gov/sites/default/files/110th-congress-2007-2008/workingpaper/2007-11_0.pdf (Internet Archive capture 20160724165600) | `e8f376a6330b320bf778ac50a8831b21fbb7884a9f9b72bea761d720f779524c` | `cbo_wp2007-11_cristia.pdf` | 2026-10-24 retrieval; 2026-10-25 checksum | Earnings/mortality methods sensitivity; section 2.2 |
| *Growing Disparities in Life Expectancy*, publication 41681 | CBO, 17 April 2008 | https://www.cbo.gov/publication/41681 (PDF capture 20260115091607) | `e22720ad1ca203c5a801e61094c17a01d050b0c57ce929fa7dcb1d09573fb467` | `cbo_41681.pdf` | 2026-10-24 retrieval; 2026-10-25 checksum | Contextual mortality synthesis and definitions; section 2.2 |
| *Implications of Differential Mortality for Analyses of Social Security Policy Options*, publication 49659 | CBO, 7 November 2014 | https://www.cbo.gov/publication/49659 (PDF capture 20250206070851) | `2bb8a546ccd305fc689f48ea841a66d34b18cb9fb08132949c6fdfcc9910aaa8` | `cbo_49659.pdf` | 2026-10-24 (historical manifest only; excluded capture not reopened) | Located mixed-content source only; safely bounded definitions remain open |
| OACT January 2025 presentation, Tiffany Bosley | SSA OACT, 14 January 2025 | https://www.ssa.gov/OACT/presentations/tbosley_20250114.pdf | `33a192b5725ef338060044533b7f9c3389dde762ddefdcaa26677bc25d468d46` | `oact_tbosley_20250114.pdf` | 2026-10-24 retrieval; 2026-10-25 checksum | January presentation identity and Study 129 link; section 2.1 |
| 2018 NHIS Person Variable Layout | NCHS, 13 June 2019 | https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Dataset_Documentation/NHIS/2018/personsx_layout.pdf | `186bb42ff139503b2a2263f227ca558dd82fab99a77c25395af66ae0fc366322` | `nhis2018_personsx_layout.pdf` | 2026-10-24 retrieval; 2026-10-25 checksum | Person covariate definitions; section 2.2 |
| 2018 NHIS Sample Adult Variable Layout | NCHS, 3 September 2019 | https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Dataset_Documentation/NHIS/2018/samadult_layout.pdf | `9ab1b5345df69c11cff74ee1921abb2d02d3b7e698061c0d08589d00012da9a0` | `nhis2018_samadult_layout.pdf` | 2026-10-24 retrieval; 2026-10-25 checksum | Adult covariate definitions; section 2.2 |
| 2018 NHIS Public Use Survey Description | NCHS, June 2019 | https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Dataset_Documentation/NHIS/2018/srvydesc.pdf | `62662706d190edd80f7225a4f228169566defe5bf6f3a2a6ae29d3f17c4c1246` | `nhis2018_srvydesc.pdf` | 2026-10-24 retrieval; 2026-10-25 checksum | Survey design and population documentation; section 2.2 |

**[frozen provenance; historical search scope]** The following catalog
captures support the original build's release inventory and bounded
search, including section 5.3. Retrieval dates come from the manifest;
all listed bytes were checksummed again on 2026-10-25. This checksum
check does not repeat the historical title search or certify absence
of other releases. Local names below are relative to the source archive.
The existing CBO 49659 digest above remains a historical manifest pin:
its excluded capture was not opened or rehashed in this fix.

| Source name | URL | Local file | SHA-256 | Access date | Reliance |
|---|---|---|---|---|---|
| OACT Actuarial Studies index | https://www.ssa.gov/oact/NOTES/actstud.html | `idx_actstud.html` | `7a76a2f355c922d88749a5d44bd20f471d522af7ffd4b504aba1ad6923486b80` | 2026-10-24 retrieval; 2026-10-25 checksum | Study discovery; bounded historical catalog scope in sections 2 and 5.3 |
| OACT studies, 2010s | https://www.ssa.gov/oact/NOTES/s2010s.html | `idx_s2010s.html` | `038e2e999c97869b8b0cadbc40383945b7e510e357fa4b990631ac0b8b5637ce` | 2026-10-24 retrieval; 2026-10-25 checksum | Study titles/dates inspected by the original build; section 5.3 search scope |
| OACT studies, 2020s | https://www.ssa.gov/oact/NOTES/s2020s.html | `idx_s2020s.html` | `5c26fc7641341dc872e6a0d151fdd428cfe9a87fec0b9872af8e574844e7d098` | 2026-10-24 retrieval; 2026-10-25 checksum | Study titles/dates inspected by the original build; section 5.3 search scope |
| OACT Actuarial Notes index | https://www.ssa.gov/oact/NOTES/actnote.html | `idx_actnote.html` | `227399105aaf4bfee2a7992ff814029e1e3decfabd559097b12fbd8f6f7821c6` | 2026-10-24 retrieval; 2026-10-25 checksum | Note discovery; bounded historical catalog scope in sections 3 and 5.3 |
| OACT recurring Note 5 editions | https://www.ssa.gov/oact/NOTES/ran5/index.html | `idx_ran5.html` | `9e7bf1e551eab1289323af7bc3e6e4e9d9cf75e906ed381970cb82da8f8e2fed` | 2026-10-24 retrieval; 2026-10-25 checksum | Located IRR editions and section 5.3 search scope |
| OACT recurring Note 7 editions | https://www.ssa.gov/oact/NOTES/ran7/index.html | `idx_ran7.html` | `958e4c85a15673e8871955f5a44104bbac59061ffa24bb5e894568767c00d77d` | 2026-10-24 retrieval; 2026-10-25 checksum | Located money's-worth editions and section 5.3 search scope |
| OACT special-topic notes, 2000s | https://www.ssa.gov/oact/NOTES/n2000s.html | `idx_n2000s.html` | `dfa83d2d15e43e28a27ae9b69c34ffb7fa31f8f3ad59cf1165eb6626e44229e1` | 2026-10-24 retrieval; 2026-10-25 checksum | Note titles/dates inspected by the original build; section 5.3 search scope |
| OACT special-topic notes, 2010s | https://www.ssa.gov/oact/NOTES/n2010s.html | `idx_n2010s.html` | `19c3b4eb349247fe05145702079da683c5eacdefff9f507f17e8f66a281faea7` | 2026-10-24 retrieval; 2026-10-25 checksum | Note titles/dates inspected by the original build; section 5.3 search scope |
| OACT special-topic notes, 2020s | https://www.ssa.gov/oact/NOTES/n2020s.html | `idx_n2020s.html` | `9637f72de9904110e06d189d4126eb7fae0b5d49be20db72b9b86e6f90d8879e` | 2026-10-24 retrieval; 2026-10-25 checksum | Note titles/dates inspected by the original build; section 5.3 search scope |
| NCHS Life Tables index | https://www.cdc.gov/nchs/products/life_tables.htm | `nchs_life_tables_index.html` | `d1a3be10233f6768c5384b7c5c37f13c1b3d0723c35b32d15b715d67717d5257` | 2026-10-24 retrieval; 2026-10-25 checksum | Located life-table release titles; section 2 and open earlier-release lookup |
| NCHS NVSR index | https://www.cdc.gov/nchs/products/nvsr.htm | `nchs_nvsr_index.html` | `63b4db70676f59e9535ea9c22621d9e51ecccdb97d2adda44dbe608b397e6974` | 2026-10-24 retrieval; 2026-10-25 checksum | Located report titles; section 2 release inventory |
| CBO publication 41681 landing capture | https://web.archive.org/web/20260904223656id_/https://www.cbo.gov/publication/41681 | `wb_cbo_41681.html` | `47dad9f3a7f5952113973a99225e5360a279f2cc4275be9d10497c04f5485066` | 2026-10-24 retrieval; 2026-10-25 checksum | Release identity and date; calibration source provenance only |
| CBO publication 44972 landing capture | https://web.archive.org/web/20260514231138id_/https://www.cbo.gov/publication/44972 | `wb_cbo_44972.html` | `c51638ad67a3a989c6932c0ae10561a00b9bc11b62a57df0196313d87c5397ed` | 2026-10-24 retrieval; 2026-10-25 checksum | Release identity and date; section 3 comparator provenance only |

**[frozen]** Tiffany Bosley's OACT presentation *Mortality by
Career-Average Earnings Level*, slide 1, is dated **14 January 2025**;
slide 3 describes an update of Study 124 (April 2018) that adds
retired-worker death rates by sex, age group and AIME; slide 23 links
**Actuarial Study No. 129**. Study 129's cover dates the study December
2024 and identifies a June 2025 correction to Figure 6. Thus the
January presentation is located and its study number is settled; use the
captured corrected study release, not an assumed January publication date.

Study 124 uses the June 2017 MBR and selected years 1995–2015; Study 129
uses the June 2023 MBR and years 1995–2022. The update extends published
ages to 85–89, adds death-rate tables, and reports annual figures through
2022. Study 124's quintile RMRs are Appendix A Tables 4–8, hypothetical
worker intervals are section II.C/Table 3 and Appendix C Tables 9–13,
and selection codes are Appendix E. Study 129's selection codes are
Appendix A, death-rate tables Appendix C Tables 1–6, RMR tables Appendix E
Tables 7–12 and annual figures Appendices D/F. Its tables have selected
years 1995, 2000, 2005, 2010, 2015 and 2020; the age support grows across
those years because only workers reaching 62 in 1993 or later enter.
Do not fill absent early age-year cells as if published.

### 2.2 Population, measures and exact source variables

**[frozen] OACT.** Study 129 sections II.A–C, printed pp. 3–5, concerns
male and female **retired-worker beneficiaries** with an available PIA,
from which AIME is derived. It excludes WEP/totalization and earlier
benefit-calculation cases and those previously entitled to disability
benefits. AIME is own career-average indexed earnings used in the PIA;
it is not total household income or an average of every observed
earnings report. Quintile breakpoints are calculated separately by sex,
calendar year and attained-calendar-year age; monthly exposure is by age
at last birthday. The current survivors are ranked anew, rather than
assigned a permanent prediction-boundary quintile.

The published bands are 62–64, 65–69, 70–74, 75–79, 80–84 and 85–89,
subject to the cohort/date support above. Annual rates divide deaths by
MBR exposure years using the source's convention that deaths generally
receive a full year's exposure at the age of death. An RMR divides a
quintile's rate by the all-AIME rate for that sex × age band × year.
Tables print rates to four and RMRs to two decimal places. Directly using
these rate ratios as annual-q multipliers is a **[proposed] mapping
assumption**, not a source identity. It must be reported alongside the
dynamic-AIME versus frozen-lifetime-rank distinction and the
beneficiary/non-beneficiary population difference.

**[frozen] NCHS education.** *Deaths: Final Data for 2022*, Table 14,
printed/PDF p. 86, gives **numbers, age-specific death rates and
age-adjusted death rates**, by sex, for ages 25–34, 35–44, 45–54 and
55–64, plus 25–64 combined. Categories are less than high school diploma
or GED; high school diploma or GED; some college or collegiate degree;
and education not stated in counts. The rates are per 100,000 resident
population; they are not annual probabilities of death. Technical Notes
pp. 127–128 explain exclusions below 25 (schooling incomplete) and at
65+ (poorer reporting), reporting completeness and the ACS denominators.
Table 14 and p. 128 use 2022 one-year ACS estimates, adjusted to
postcensal July 1 resident totals. There is no education mortality target
at 65+ in this table. Earlier editions' availability stays **[open]**.

**[frozen] NCHS race and Hispanic origin.** NVSR 74(2) and 75(5),
*United States Life Tables, 2022/2024*, Tables 1–18, give total, Hispanic,
and non-Hispanic AIAN, Asian, Black and White life tables by sex.
P. 2 defines `q_x` as the probability of dying between exact ages x and
x+1 and `e_x` as remaining period life expectancy. Race is single race
under the 1997 standards. P. 2 explains race/origin misclassification
adjustments; Medicare supplementation at 66–99 applies to total, Black
non-Hispanic and White non-Hispanic tables, while older Hispanic, AIAN
and Asian mortality is modeled. The terminal 100+ interval does not
identify separate annual q values for ages 100–120.

**[frozen findings] Public NHIS–LMF.** The 2019 public LMF description
pp. 1–4 covers NHIS 1986–2018 interviews with mortality follow-up through
31 December 2019. Linkage-eligible adults have `MORTSTAT` (assumed
alive/deceased, not perturbed); NHIS `DODYEAR`/`DODQTR` are in codebook
p. 3. Follow-up/cause may be synthetic for selected records. The
person-month fields belong to NHANES, not NHIS. The description p. 4
specifies merge by `PUBLICID`; codebook p. 4 defines eligibility-adjusted
`SA_WGT_NEW` (sample adults 1997–2018) and `WGT_NEW` (persons 1987–2014).
For 2015–2018, mortality analysis uses sample adults; the public-file
description p. 2 states the linkage restriction.

The 2018 NHIS Person Layout p. 294 defines `EDUC1`, highest completed
schooling/degree: 00–12 below high school, 13–14 GED/high school,
15–17 some college/associate degree, 18–21 bachelor or higher; 96–99
require their explicit missing/inapplicable treatment. Sample Adult
Layout p. 7 defines `SEX`, p. 8 `HISPAN_I` (00–11 Hispanic, 12
non-Hispanic), p. 9 `RACERPI2` (White only, Black only, AIAN only, Asian
only, unreleasable race group, multiple race), and p. 11 `AGE_P`
(single ages through 84, pooled 85+). Person and adult files merge by
survey year/household/family/person identifiers (Survey Description
p. 71); pseudo-stratum/PSU variables are `PSTRAT`/`PPSU` (Adult Layout
p. 6). Earlier years' harmonization is **[open]**.

**[frozen settlement, limited scope]** The documented public package
supports joint education × race/Hispanic-origin × sex associations at
interview ages 65–84 and pooled 85+, subject to survey precision, linkage and
censoring. It does not identify each single age above 84 and supplies no
administrative lifetime-earnings/AIME history. A three-dimension joint
gradient conditional on lifetime earnings therefore remains **[open]**.
NHIS suppresses birth month/year (Survey Description p. 25); public death
time is quarter/year. Single attained-age × calendar-year q therefore
requires registered interval-censoring and birthday reconstruction, not
direct observation of every required coefficient. The record has not
established that restricted-use linked files solve
that problem; they stay excluded. No restricted file is requested or
needed to proceed with the documented public education/race route.

**[frozen] Cristia 2007 sensitivity definitions.** CBO Working Paper
2007-11, sections II.1–II.3, printed pp. 7–12/PDF pp. 9–14, constructs
men's and women's person-years at ages 35–75 from the 1984, 1993, 1996
and 2001 SIPP panels linked to SSA earnings/benefit/death records, covering
1983–2003. Later follow-up carries forward the last SIPP covariates.
Taxable SER earnings through 1977 include above-cap imputation; 1978–1979
are interpolated; 1980–2003 DER measures include wages/tips, deferred
wages and Medicare-taxable self-employment earnings. The PCE deflator
expresses earnings in 2000 dollars. At age 53+, the primary earnings
average covers ages 41–50; below 53 it covers `max(28,A−12)` through
`A−3`. Surviving persons are ranked within sex × five-year-age ×
five-year-birth-cohort groups. Census-based weights match sex, age,
race/Hispanic origin and calendar period. These definitions differ from
OACT AIME and SM3's fixed-boundary partial-career proxy.

Section III.1, printed p. 14/PDF p. 16, defines directly age-standardized
one-year mortality ratios relative to all same-sex persons in the age
band. Section III.2, printed p. 18/PDF p. 20, and Tables 5–6, printed
pp. 38–39/PDF pp. 40–41, fit separate male/female next-year-death logistic
models for ages 35–49, 50–64 and 65–75, with bottom earnings quintile as
reference. Controls successively add age/birth year, race/Hispanic
origin, marital status and education. **[open mapping]** An odds ratio
is not an SM1 relative risk. Reconstruct predicted probabilities on a
registered reference population, then change to SM1's `q3` reference;
do not insert log odds ratios as log relative risks.

**[frozen] CBO 41681's role.** *Growing Disparities in Life Expectancy*
(17 April 2008) is a research synthesis, not a fresh coefficient dataset.
P. 1 footnote 1 defines period life expectancy. Pp. 2–3 and Figure 2
summarize county socioeconomic and education contrasts rather than
individual lifetime-earnings quintiles. **[proposed]** Use it as context
for registered sensitivities/path choices, never as an independent raw
coefficient table or unused mortality holdout. CBO 49659's mixed-source
methods remain open pending a safely bounded definitions-only extract.

### 2.3 The complete SM1 input contract and proposed loader

**[frozen interface]** At #570 `0c226e3f`,
`mortality_ses/specification.py` defines all three required dimensions;
SM1 supplies no empirical categories. Each `RiskDimension` needs a name,
its own frame-column name, ordered string categories, a member reference
category and explicit `unclassified_values`. Every named path year must
contain each category × `female`/`male` × single age 0–120 exactly once,
with columns `dimension`, `category`, `sex`, `age`,
`log_relative_risk`; inclusive `age_lower`/`age_upper` may replace `age`.
The reference coefficient must be exactly zero. Individual and combined
exponentiated risks must be finite and positive.

**[proposed schema]** Freeze these inputs together with SM3's group
construction before SM2 produces a table; category strings are interface
choices, not categories claimed to be supplied by SM1:

| Dimension | Proposed frame column | Ordered categories | Reference | Explicit unclassified treatment |
|---|---|---|---|---|
| `lifetime_earnings` | `sm_lifetime_earnings_quintile` | `q1`, `q2`, `q3`, `q4`, `q5` | `q3` | missing and registered construction-failure codes |
| `education` | `sm_education` | `less_than_high_school`, `high_school`, `some_college`, `college` | `high_school` | missing and registered unknown/inapplicable codes |
| `race_hispanic_origin` | `sm_race_hispanic_origin` | `hispanic`, `white_non_hispanic`, `black_non_hispanic`, `other_non_hispanic` | `white_non_hispanic` | missing and unresolved origin/race codes |

**[frozen crosswalk warning]** Existing `estimates/group_breakdown.py:1227–1274`
uses five MINT bands: <12, 12–13, 14–15, 16 and ≥17 years. Its race
scheme (`:1103–1130`) uses `hispanic_any_race`; the attribute builder uses
`hispanic`. SM's proposed four education groups and Hispanic string are
therefore an explicit new crosswalk; neither silently reuses MINT labels
nor changes the out-of-scope GR definitions.

Years of education mapped from the existing source are a separate
definition from highest degree; a GED and partial college cannot silently
change categories. The three-level NCHS education target pools
`some_college`/`college`, so it cannot identify their difference. NHIS may
supply that contrast. NHIS race group 05 is not a disclosed detailed race;
the source's origin/race imputation must remain documented. The proposed
“other” group contains populations without an NCHS life table; do not
represent an AIAN/Asian-only weighted average as the full other group.

**[proposed loader]** OACT RMRs provide reference contrasts
`log(r_q) - log(r_q3)` for supported source sex × band × year cells.
Expanding a band to constant single-age coefficients is an explicit
interpolation assumption. The registered source-year matrix must state
what happens before an age band first appears. The source provides no
earnings contrast below age 62 or at ages 90–120; the treatment of those
ages is **[open]**, with downward/upward extrapolation or a compatible
Cristia sensitivity named before fitting. A source gap cannot be encoded
as an empirical zero effect.

NCHS Table 14 supplies age-band education rate contrasts relative to
high school, requiring an explicit rate-to-q mapping. Public NHIS–LMF
supplies a possible survey-estimated residual contrast at 65–84 and
pooled 85+, with an explicit tail assumption. NCHS life tables supply
race/origin q contrasts for observed single-age intervals. The terminal
100+ rule and any unsupported other-group coefficient stay **[open]**.

SM1's `HoldLastCoefficientPath` takes `year`, holds between observations
and after the final year, and refuses years before the first table. The
published table knots are 1995, 2000, 2005, 2010, 2015 and 2020, with
missing coverage filled only by registered assumptions. Annual figures
continue through 2022. Q6 therefore requires the primary path to hold the
last observed 2022 gradient; extraction/digitization, its uncertainty and
complete coefficient coverage remain **[open]**. A 2020 table-only path is
a proposed registered sensitivity. Using it as primary would require an
explicit amendment to Q6, which this audit does not make. Widening needs a custom
`CoefficientPath` with named slope, origin, applicable ages and caps,
which remain **[open]**. Education/race knot years and synchronization of
all dimensions in one complete table must be registered explicitly.

**[frozen]** The mechanism log-adds all dimensions and renormalizes in the
deployment population; its DI configuration determines fixed DI-origin
rows, held at baseline q before the DI adapter. This agrees with excluding
disabled-origin persons from the fitted earnings target in direction,
but does not prove equality of the source and model's DI definitions.
Register `unclassified_rule="reference"` **[proposed]** if an unclassified
person must remain in SM3's overall expected-death denominator; `refuse`
is SM1's default. Neither rule assigns that person a reported group cell.

**[open: identification]** Marginal source contrasts do not determine
mutually adjusted three-dimension coefficients. Correlation can cause
double counting or other distortion, but does not prove a particular
direction of error. Freeze a joint route and its reference distribution
before fitting. A sensitivity that simply adds marginal effects must say
so. Public NHIS can estimate education/race association; Cristia 2007's
SIPP–SSA logistic models offer a historical lifetime-earnings sensitivity
with controls, rather than a current joint distribution for this cohort.
PSID use follows the project's data-access record.

### 2.4 Availability, exposure and holdout

**[frozen]** All calibration sources here are exposed targets, not unused
holdouts. Source reference/publication dates are Study 124 1995–2015 /
June 2017 MBR / April 2018; Study 129 1995–2022 / June 2023 MBR /
December 2024, presentation 14 January 2025, corrected figure June 2025;
NCHS 2022 life tables 2022 / 8 April 2025; NCHS 2024 life tables 2024 /
25 August 2026; final deaths 2022 / 10 June 2025; public NHIS–LMF
interviews 1986–2018, follow-up through 2019 / codebook 28 April 2022,
description May 2022; 2018 NHIS interviews 2018 / survey description
June 2019, person layout 13 June 2019, adult layout 3 September 2019;
Cristia SIPP panels 1984, 1993, 1996, 2001 with administrative earnings
and mortality through 2003 / August 2007; CBO 41681 / 17 April 2008.
The exact release dates of any earlier NHIS cohort used are **[open]**.

SM2 claims no prospective prediction origin. Its primary update was not
available before 2011 and shares calendar years with SM3's outcomes.
An independent, unused comparison source and a narrower, dated training
partition must be explicitly frozen before calling any accompanying fit
check out of sample. None is established here. The section-11 and run
artifact exposure metadata in SM3 applies to the lane's history; this
audit read public mortality targets, not any run artifact value.

### 2.5 Cells, bounds, pass conjunction and power

**[frozen tolerance; proposed operationalization]** Retain the design's
0.1-year maximum discrepancy in fitted period life expectancy at 65 for
every earnings-group target fitted. OACT publishes RMRs rather than e65;
register a target obtained by applying its source ratios to the same
baseline, with a fixed reference population, marginalization and tail
rule. Do not silently replace this by matching only coefficients.
For NCHS fitted life-table targets, retain the same 0.1-year limit and
the source's age/closing conventions. Whether the different source
populations/baselines can satisfy these simultaneously remains **[open]**.

Add exact conformance to printing intervals for every published fitted
RMR: a positive two-decimal `r` represents its registered rounding
interval bounded by `r-0.005` and `r+0.005`; use the transformed endpoints
and reference-category interval when testing log contrasts. Do not use
the approximation `0.005/r` as an exact log tolerance. Any additional
residual tolerance is registered before fitting and cannot relax e65.
The critical family is **all** fitted source × category × sex × supported
age × source-year targets; its integer size and inclusion of each
joint-survey target are **[open until the loader plan is frozen]**.

**[frozen uncertainty requirements]** Use simultaneous 95% intervals with
Bonferroni allocation over that family. Resampling of NHIS must respect
survey strata, PSUs and family clusters; ACS-denominator uncertainty must
respect ACS design/replicate weights. Do not use independent-person
bootstrap or call complete death registration a zero-uncertainty rate.
Separate rounding, random mortality variation, survey sampling and
linkage/perturbation sensitivity. Preserve shared-source covariance
across calibration targets. If a source does not publish the uncertainty
needed for a required target, that item stays open or inconclusive.

Numerical/Monte Carlo error must be below one tenth of each tolerance:
less than 0.01 year for the life-expectancy comparison and less than one
tenth of the corresponding registered ratio residual tolerance. Exact
deterministic reconstruction has no simulation error. A simultaneous
bound that is too wide is inconclusive, never a conformance pass.

**[proposed named procedure]** `SM2_SOURCE_RECONSTRUCTION_AND_CLUSTER_BOOTSTRAP`:
validate a complete SM1 table; reconstruct source estimands on a fixed
reference population/baseline; preserve source printing intervals;
propagate source uncertainty by the registered survey/cluster procedure;
require every simultaneous residual interval inside every tolerance,
all life-table invariants, registered e65 ordering and permutation
invariance. No outcome is admitted until all required source mappings,
identification choices, family size and tail rules are frozen. This is
calibration conformance, so no independent predictive 0.90-power claim
is made for SM2; the separate held-out test is SM3.

**[proposed suppression]** At least 100 unweighted persons per published
microdata-derived subgroup, using the SSA MINT8 Table User Guide's
“Sample Size Restrictions”, `#sample-size`, minimum already cited in the
SM3 section. Suppress the entire subgroup and complementary values that
would reveal it. This is a publication rule, not a precision guarantee.

**[frozen named-condition handling]** If comparable gradients disagree
beyond the frozen fit tolerance, `GRADIENT_SOURCES_INCONSISTENT` makes
OACT primary and all others registered sensitivities; nothing is tuned
to force agreement. It is **not yet assessed**, rather than triggered by
different populations alone. `SOURCE_UNAVAILABLE` / open identification
applies to the complete modern three-dimension joint source and missing
source-age mappings. `EXPOSURE_UNRESOLVED` blocks any claim to an unused
holdout not established by a dated exposure record.
`FRAME_ATTRIBUTE_MISSING`, `SMALL_CELL_DISCLOSURE`,
`CELL_CONSERVATION_BROKEN` and `GATE_FAIL_OR_REGRESSION_FAIL` apply if
their stated triggers occur. Inadequate joint-target precision is
inconclusive; no route avoids `WEAK_POWER_OR_VACUITY` merely by being
called calibration if a claimed test is uninformative.

## 3. SM4: lifetime-benefit consequences

**[frozen]** SM4 is a registered **report-only comparison**, not an
admission gate. It reports lifetime benefits and benefit-to-tax ratios by
the registered lifetime-earnings dimension with and without differential
mortality. OACT is the first located comparator; PWBM is located at
S0.2; CBO is second; Urban reaches it only through a validation lane's
cleared labels-only or definitions-only extract. No SM4 comparator value
is transcribed here.

### 3.1 Located releases and definitions

**[frozen locators]** These four OACT notes were retrieved on
24 October 2026. They are located vintages; no assertion that a later
release cannot exist is needed.

| Note | Date | URL | SHA-256 | Local file | Access date | Reliance |
|---|---|---|---|---|---|---|
| Actuarial Note 2024.5, *Internal Real Rates of Return Under the OASDI Program for Hypothetical Workers* | September 2024 | https://www.ssa.gov/oact/NOTES/ran5/an2024-5.pdf | `7d7c1423b1016084ffb5453bbd4186a45c9cf6db4a1011eca3fa016c2a108000` | `oact_an2024-5.pdf` | 2026-10-24 retrieval; 2026-10-25 checksum | Hypothetical-worker definitions and scheduled-scenario locators only; section 3.1 |
| Actuarial Note 2025.5, same title | December 2025 | https://www.ssa.gov/oact/NOTES/ran5/an2025-5.pdf | `a3f632fb04f4a59282c4a5f928e07da4361fba351ac9aac504d9ae579052fd67` | `oact_an2025-5.pdf` | 2026-10-24 retrieval; 2026-10-25 checksum | Hypothetical-worker definitions and scheduled-scenario locators only; section 3.1 |
| Actuarial Note 2024.7, *Money's Worth Ratios Under the OASDI Program for Hypothetical Workers* | October 2024 | https://www.ssa.gov/oact/NOTES/ran7/an2024-7.pdf | `de0c101de512e26f071cd7eba03b84effccc372388ff80fc944edf28c76a0a08` | `oact_an2024-7.pdf` | 2026-10-24 retrieval; 2026-10-25 checksum | Hypothetical-worker definitions and scheduled-scenario locators only; section 3.1 |
| Actuarial Note 2025.7, same title | December 2025 | https://www.ssa.gov/oact/NOTES/ran7/an2025-7.pdf | `478d40a0829dc7cdb586fefa2ea3e6eaf75bc18b3bd42564ed4897477e18e207` | `oact_an2025-7.pdf` | 2026-10-24 retrieval; 2026-10-25 checksum | Hypothetical-worker definitions and scheduled-scenario locators only; section 3.1 |

OACT 2025.5 p. 1 defines IRR as the real annual yield equating the present
values of expected benefits and payroll contributions. OACT 2025.7 p. 1
defines money's worth as present value of expected benefits divided by
present value of expected payroll contributions. Footnotes 1–2 of each
include employee/employer contributions and general-fund replacements
but omit income-tax-on-benefit transfers. Pp. 2–3 define hypothetical
scaled very-low/low/medium/high earners and steady-maximum earners,
single men/women, one-earner couples and selected two-earner couples,
and which retirement, disability and auxiliary/survivor payments enter.
These are hypothetical earnings levels, not empirical quintiles.

For 2025.5, the earnings-level crosswalk is Table A p. 4 and scheduled
comparators are Table 1 p. 6 and Table 4 p. 9. For 2025.7, Table A is
p. 4 and scheduled comparators are Table 1 p. 8 and Table 4 p. 11.
The notes p. 1 give the relevant Trustees-assumption vintage and
pre-Public-Law-119-21 current-law caveat; no Trustees table is used here.
P. 4 explicitly cites Study 129 as an input to the differential-mortality
adjustment: this comparison is not independent validation of that input.

**[proposed comparator scope]** Freeze the scheduled-benefit scenario
only. Defer increased-payroll-tax/payable-benefit scenarios and their
financing assumptions to the appropriate later validation workflow.
Study 124 section II.C/Table 3 defines hypothetical-worker AIME intervals
by midpoints; it does not prove that either its old numerical cutpoints
or population shares are current. Any crosswalk from empirical quintiles
must be new, dated, defined and labeled; unresolved definition differences
are reported, never erased by relabeling.

| Located CBO release | Publication date | URL | SHA-256 | Local file | Access date | Reliance |
|---|---|---|---|---|---|---|
| *The 2013 Long-Term Projections for Social Security: Additional Information*, publication 44972 | 17 December 2013 | https://www.cbo.gov/sites/default/files/113th-congress-2013-2014/reports/44972-SocialSecurity.pdf | `720393d8c3a938252d341e127716794b674ed1004926f367ed9b66786e30cc91` | `cbo_44972.pdf` | 2026-10-24 retrieval; 2026-10-25 checksum | Lifetime-measure definitions and locators only; section 3.1 |

**[frozen located CBO source]** *The 2013 Long-Term Projections for Social
Security: Additional Information*, publication 44972, 17 December 2013,
is captured with URL/size/SHA in the main manifest. Exhibit 10 printed
p. 16/PDF p. 20 gives the median present value of retired-worker
benefits. Exhibit 13 printed p. 19/PDF p. 23 gives median lifetime taxes
and a broader benefit scope; Exhibit 14 printed p. 20/PDF p. 24 gives
**median lifetime benefits divided by median lifetime payroll taxes**.
The notes define both payroll-tax shares and discount the inflation-adjusted
cash flows to age 62. Printed p. 13/PDF p. 17, footnote 1, ranks people
surviving to age 45, defines lifetime household earnings as present value
of own real earnings for an always-single person and a function of own
and spouse earnings adjusted for household economies of scale in married
years, and specifies a 3.0% real discount rate. Footnote 2 subtracts
income tax on benefits credited to Social Security but retains tax
credited to HI. Exhibit 13 excludes young-widow and child benefits before
1984 because their histories are unavailable. The exact household
economies-of-scale formula is **[open]**; the source's phrase does not
identify it. A ratio of medians must not be replaced by a mean of
individual ratios or by a ratio of means.

CBO 49659, the 7 November 2014 differential-mortality presentation, is
located but includes excluded mixed content. It was not reopened in this
continuation. Any claim about its joint mortality model or lifetime
measure definitions requires a safely delimited definitions-only extract.
A newer CBO lifetime-benefit vintage is **[open]**, rather than required
for a comparison registered to the already located 2013 release.

### 3.2 Population, dates, exposure and critical comparison cells

**[frozen dependencies]** Population claims require SM3; an SM2-only
exercise remains calibrated. Lifetime measures require admitted payment
and covered-earnings histories, entrants, and a horizon that covers the
registered lifetime measure. National claims also require the
representative population. No imputed/scaled population substitutes for
that dependency.

**[proposed finite comparison family]** Use every supported sex,
birth-cohort, earnings-profile and family-profile label in the selected
OACT scheduled Tables 1 and 4, plus every supported birth-cohort,
earnings-category and sex label in CBO Exhibits 10, 13 and 14. Publish
each source measure separately; no implied one-to-one crosswalk removes
a source cell. The actual label enumeration and integer family size are
**[open]** pending the registered definitions extract, and must be frozen
before any projection comparison.

**[open]** Before running, freeze sex/cohort/family/earnings cells,
birth-cohort and payment dates, discount basis, tax shares, gross/net
benefits, inclusion of DI and auxiliaries, rank population, survivor
conditioning, and scheduled-law vintage. OACT's Notes 2024/2025 use
their respective assumption vintages; Table A administrative retirement
years are specified in that table. CBO's 2013 release is a model
projection available December 2013, not an unused later outcome.
The model's starting-frame and covariate interview/release dates remain
**[open until those dependencies exist]**.

**[frozen exposure]** This continuation viewed definitions and captions with outcome numbers
masked or omitted; definitional ages and discount conventions are retained.
It transcribed no comparator outcome value. The
original audit's manifest records its mixed-CBO stop. The design lane's
section-11 exposure to published group results remains on the record;
the mortality/groups lane cannot become an unexposed builder of Urban
comparisons. Only a separately cleared validation-lane extract may supply
Urban's definitions. No blindness is claimed for an exposed comparison;
its registration is labeled post hoc. Being report-only does not itself
establish an unused holdout.

### 3.3 Uncertainty, precision and publication conjunction

**[frozen classification]** There is no SM4 numerical pass tolerance or
0.90 pass-power estimand in the approved design; assigning either would
turn a report-only comparison into an unapproved gate. Report every
registered gap and all definition mismatches. The named procedure is
**[proposed]** `SM4_PAIRED_LIFETIME_COMPARISON`: common simulation draws
for with/without-gradient measures; paired family/survey-design
resampling; Bonferroni simultaneous 95% bounds over the complete
registered cell/measure family; preserve comparator rounding and
uncertainty. The model output, denominators, bounds and refusals all
remain in the report. A wide interval is inconclusive for any
interpretation of agreement, never a pass.

**[open before running]** Freeze a substantive reporting precision target
in each measure's units, since there is no source-comparison tolerance.
Monte Carlo error must be below one tenth of that target; dependency
gate tolerances remain binding and cannot be replaced by an SM4
precision target. If no meaningful target is registered, no precision or
power claim is made. This audit's invented SM3/ED2 simulations do not
establish lifetime-comparison precision.

**[proposed suppression]** At least 100 unweighted persons per published
model subgroup, SSA's `#sample-size` minimum, with whole-subgroup and
complementary suppression. No hypothetical source worker count is
misrepresented as an empirical subgroup denominator.

**[frozen publication conjunction]** Report only after definitions,
source hashes/dates, cells, horizon/population dependencies, uncertainty
procedure and suppression rule are registered; label every unadmitted
population/horizon/calibrated mechanism. `SOURCE_UNAVAILABLE` applies
when a required comparator definition cannot be supplied, not merely
because an optional newer vintage was not found. PWBM remains deferred
to S0.2. `EXPOSURE_UNRESOLVED` applies to unestablished blindness;
`SMALL_CELL_DISCLOSURE`, `FRAME_ATTRIBUTE_MISSING`,
`MORTALITY_CHANGE_UNADMITTED`, `SUCCESSOR_EXHAUSTED` and
`GATE_FAIL_OR_REGRESSION_FAIL` apply through their dependencies.
`SCALED_NOT_SIMULATED` withdraws affected national figures. The design's
`HORIZON_NOT_LICENSED` condition is formally stated for F5; SM4's own
required lifetime horizon is still an explicit dependency, without
silently extending that named condition's trigger. No new numerical
source-disagreement or pass/fail condition was triggered by this audit.

## 4. ED1: education transitions on public CPS microdata

### 4.1 Sources and verification scope

[frozen] The code release is Microcosm
`dce4aa99bef166a700713557c66f67d318f0271f`, committed 24 October 2026 at
14:13:24 UTC. The supporting inputs below were retrieved on 24 October
2026. Their local file names are relative to
`EV/mortality-groups-financing-20261021/s0_1-sources/`. Each listed
SHA-256 was verified against the saved file. The immutable code URLs pin
repository paths at that commit. The code-source pins do not establish
that a particular frame release carries all corresponding columns.

| Supporting input | URL | Local file | SHA-256 | Access date | What this note relies on |
|---|---|---|---|---|---|
| Microcosm immutable commit metadata | https://api.github.com/repos/PolicyEngine/microcosm/commits/dce4aa99 | `ed_microcosm_dce4aa99_commit.json` | `ea570b7f58bed7ad2f01b481d5ab17870b915e867d48d799a892b111cdb0321b` | 2026-10-24 | Code snapshot identity and commit date cited in section 4.1. |
| Microcosm ASEC source-pin documentation | https://raw.githubusercontent.com/PolicyEngine/microcosm/dce4aa99bef166a700713557c66f67d318f0271f/docs/us-asec-source-pins.md | `ed_microcosm_us-asec-source-pins.md` | `835ec029d4ac1a8592d0424398894df2ef43b9c7568e4e10ea2df6ee84154a1f` | 2026-10-24 | Processed-source revisions and income/survey-year crosswalk in sections 4.1 and 4.4. |
| Microcosm ASEC education-assistance source code | https://raw.githubusercontent.com/PolicyEngine/microcosm/dce4aa99bef166a700713557c66f67d318f0271f/packages/microcosm-build/src/microcosm/build/us_runtime/education_assistance_source.py | `ed_microcosm_education_assistance_source.py` | `7b5df9556b89fc623f80c2db9af91e33bdc1806d2fbbe0a183a596f4fec2a150` | 2026-10-24 | Declared archive/member pins and the documented cache path in section 4.1. |
| Microcosm processed ASEC source declarations | https://raw.githubusercontent.com/PolicyEngine/microcosm/dce4aa99bef166a700713557c66f67d318f0271f/packages/microcosm-build/src/microcosm/build/us_runtime/asec_sources.py | `ed_microcosm_asec_sources.py` | `ac6d36efd3d635a88395c112eeb9dd0337c6abefe482f33492cd544abea4c52c` | 2026-10-24 | Processed ASEC file names and immutable source revisions in section 4.1. |
| Microcosm ASEC source-pool code | https://raw.githubusercontent.com/PolicyEngine/microcosm/dce4aa99bef166a700713557c66f67d318f0271f/packages/microcosm-build/src/microcosm/build/us_runtime/asec_pool.py | `ed_microcosm_asec_pool.py` | `57ee476b1dac6250db4d352fd5a942acb533d31debe721e455e60ff677b4ff3c` | 2026-10-24 | Default versus selectable training years in section 4.1. |
| Microcosm ACS PUMS source code | https://raw.githubusercontent.com/PolicyEngine/microcosm/dce4aa99bef166a700713557c66f67d318f0271f/packages/microcosm-build/src/microcosm/build/us_runtime/acs_pums.py | `ed_microcosm_acs_pums.py` | `f77f67e6c3f1b755173ac96e7a0c5312c46f4a8831edc29775ee1d5d76a0bf75` | 2026-10-24 | Reviewed ACS spine reference vintage in section 5.2. |
| Microcosm U.S. source mappings | https://raw.githubusercontent.com/PolicyEngine/microcosm/dce4aa99bef166a700713557c66f67d318f0271f/packages/microcosm-build/src/microcosm/build/us/spec/sources.yaml | `ed_microcosm_sources.yaml` | `bad35a1e635c406633ab74fc23b53d22f8a6ff3f5c101f1d30317ca6395241be` | 2026-10-24 | Within-household parent-pointer resolution and the checked source mappings in section 4.2. |
| Microcosm ASEC Census person-column documentation | https://raw.githubusercontent.com/PolicyEngine/microcosm/dce4aa99bef166a700713557c66f67d318f0271f/docs/us-asec-census-person-columns.md | `ed_microcosm_us-asec-census-person-columns.md` | `e05ea77edeb5d068935adfdb7e74992721a5ea661931638bf56ccff94dc9b0ab` | 2026-10-24 | Declared person columns and the limits of the checked frame-column evidence in section 4.2. |
| Census 2025 ASEC Public Use Data Dictionary | https://www2.census.gov/programs-surveys/cps/datasets/2025/march/asec2025_ddl_pub_full.pdf | `census_asec2025_ddl_pub_full.pdf` | `5cb80973326ef8b625fbaae70d80b0c641ce5d2b3911abd2fb4427abd5908a6f` | 2026-10-24 | Variable definitions, parent-pointer universe and printed locators in section 4.2. |
| Census CPS ASEC 2025 public-use CSV archive | https://www2.census.gov/programs-surveys/cps/datasets/2025/march/asecpub25csv.zip | `census_asecpub25csv.zip` | `318845a2b5e0034eb2973898de1738f4df0025727de38499e7669cb9c0deef0b` | 2026-10-24 | Original attempt's archive-byte provenance; this fix hashes only and does not unpack or inspect person contents. |
| Census CPS technical documentation: 2023 | https://www.census.gov/programs-surveys/cps/technical-documentation/complete.2023.html | `ed_census_cps_complete2023.html` | `805641399dfccbed8201005574bb5c855d7c716144ee02c2df3fd92680d557b7` | 2026-10-24 | Documentation links and revision-date limits in section 4.4. |
| Census CPS technical documentation: 2024 | https://www.census.gov/programs-surveys/cps/technical-documentation/complete.2024.html | `ed_census_cps_complete2024.html` | `1d15cbbfc6ed60e40ac753075a98789e43d19100090f3224ae1d318028d0b0c5` | 2026-10-24 | Documentation links and revision-date limits in section 4.4. |
| Census CPS technical documentation: 2025 | https://www.census.gov/programs-surveys/cps/technical-documentation/complete.2025.html | `ed_census_cps_complete2025.html` | `a13934ad554beca5fece172e438d3f13cf0eb62611fe4953b8085bb8e3a14544` | 2026-10-24 | Documentation links and revision-date limits in section 4.4. |
| Census CPS technical documentation: 2026 | https://www.census.gov/programs-surveys/cps/technical-documentation/complete.2026.html | `ed_census_cps_complete2026.html` | `fc1665973a14e59f1a2d0bd6f338a557c35b0dda36463b0fc9c48b467ec2335e` | 2026-10-24 | Documentation links and revision-date limits in section 4.4. |

- `packages/microcosm-build/src/microcosm/build/us_runtime/education_assistance_source.py`,
  `ASEC_EDUCATION_ASSISTANCE_ARCHIVES`, lines 100–193, declares the Census
  person archives below. The function
  `fetch_asec_education_assistance_source` caches them under
  `~/.cache/microcosm/cps/asec_education/` by default (lines 257–275).
- `us_runtime/asec_sources.py`, lines 1–150, declares processed
  `census_cps_2022.h5` through `census_cps_2025.h5` at
  `policyengine/microcosm-us-sources`. Income years 2022–2024 are pinned to
  revision `78acc83ea8b099a97cb0d658bbed91ea75aae8b0` (public mirror,
  18 September 2026); income year 2025 to
  `efe5e2107b252506ea9b868071967cf73cc410bc` (27 September 2026).
  The default pool is income years 2023–2025, hence ASEC 2024–2026.
  Earlier pinned years remain selectable; ED1's precise training pool
  must be registered rather than inferred from the list of available pins.

| Survey year (income year) | Declared archive URL | Archive SHA-256 | Person member | Member SHA-256 |
|---|---|---|---|---|
| 2023 (2022) | https://www2.census.gov/programs-surveys/cps/datasets/2023/march/asecpub23csv.zip | `d2e000250782adfbdd7f29c82b66d866591a30f0d330496698ec19f9c784ce11` | `pppub23.csv` | `19b56537e50e7663f954361ef2bb5ce9cef8d9d45f156fe1a69a99b654198ffe` |
| 2024 (2023) | https://www2.census.gov/programs-surveys/cps/datasets/2024/march/asecpub24csv.zip | `cdb39cdac34bef99dd0940ab28e306f692404c2eea44d85dfd634214872a0a09` | `pppub24.csv` | `21a2b9e0e4b08534563578a45acad77868af4ae9a7d46f23776b707d4a559aa7` |
| 2025 (2024) | https://www2.census.gov/programs-surveys/cps/datasets/2025/march/asecpub25csv.zip | `318845a2b5e0034eb2973898de1738f4df0025727de38499e7669cb9c0deef0b` | `pppub25.csv` | `06921fe83fc66c907e6c7b86b82255dc70458ee7d76258fc48297cb34f0c06b5` |
| 2026 (2025) | https://www2.census.gov/programs-surveys/cps/datasets/2026/march/asecpub26csv.zip | `fe819d0d2fc4470c282e76c247b8aa8b6054811619730307e9f2fe6186707d93` | `pppub26.csv` | `f78920699bf671cc211cb720ff8c6274392524a22138aedaf9e3954f91ba4334` |

[frozen scope] The preserved attempt retrieved the 2025 archive and recorded
its archive/member verification in the manifest. This continuation read
code and documentation only; it did not open or tabulate person records.
[open] The other three raw archives and the per-year variable dictionaries
remain to verify. No individual attainment distribution is frozen here.

### 4.2 Variables, definitions and links

[frozen for ASEC 2025] Census's *2025 ASEC Public Use Data Dictionary*,
retrieved 24 October 2026, SHA-256
`5cb80973326ef8b625fbaae70d80b0c641ce5d2b3911abd2fb4427abd5908a6f`,
provides these definitions. The precise2023,2024 and 2026 layouts remain
[open] until their documentation is checked.

| Purpose | Definition and locator |
|---|---|
| Attainment | `A_HGA`, item18h:0 children;31–38 less than first grade through 12th grade without diploma;39 high-school diploma or equivalent;40 some college/no degree;41 occupational/vocational associate;42 academic associate;43 bachelor's;44 master's;45 professional;46 doctorate (printed 6C-3). |
| Age/cohort | `A_AGE`:0–79 single ages,80 means80–84,85 means85+ (6C-2). No exact date of birth is supplied by these items. Survey year minus interview age is an age-defined cohort proxy, not an exact birth year. A start-of-year proxy must register its birthday displacement explicitly. |
| Sex | `A_SEX`:1 male,2 female (6C-3). |
| Race/Hispanic origin | `PRDTRACE`:26 race combinations (6C-7); `PEHSPNON`:1 Spanish/Hispanic/Latino,2 no (6C-6); `PRDTHSP`:0 not in universe,1 Mexican,2 Puerto Rican,3 Cuban,4 Dominican,5 Salvadoran,6 other Central American,7 South American,8 other Hispanic (6C-7). The coarsening and Hispanic-priority rule are proposed, not a source definition. |
| Links | `PEPAR1` and `PEPAR2`:within-household parent roster line1–16,−1 no parent present; `PH_SEQ` household key, `A_LINENO` roster line, `PERIDNUM` unique person identifier (6C-1). `PEPAR1TYP`/`PEPAR2TYP`:−1 absent,1 biological,2 step,3 adopted (6C-6). |
| Weight | `MARSUPWT`, ASEC supplement final weight (6C-2). |
| Enrollment | `A_ENRLW`, last-week high-school/college/university enrollment, universe16–54 (6C-2); `A_HSCOL`, high-school versus college/university conditional on enrollment (6C-3). |

[frozen] Parent pointers have universe **all persons**, with no maximum
child age in the dictionary (6C-1). Thus links can exist throughout ED1's
16–35 range; they identify co-resident biological, step or adoptive
parents and do not recover absent parents. This is a statement about the
layout, not age-specific empirical coverage. Microcosm's
`us/spec/sources.yaml:2310–2350`, `eligibility_inputs`, resolves the
pointers within `PH_SEQ` into `parent_1_id` and `parent_2_id`, assigning0
when absent or unresolved.

[proposed] Parents' highest observed attainment is used only when a
pointer resolves; absence is a separate category at every age. The
parental channel is conditional on co-residence. No age cutoff inferred
from observed coverage is frozen. The reviewed source mappings do not
establish an exported attainment column; the approved design's finding
that the checked frame releases lack education remains the downstream
constraint. A new frame release must be checked before that condition is
cleared.

### 4.3 Population, estimands, cells and tolerance

[proposed] ED1 fits attainment from 16 through 35 by age-defined birth
cohort, sex, race/Hispanic origin and linked parental attainment. Its five
categories are less than high school (`A_HGA`31–38); high school/equivalent
(39); some college/associate(40–42); bachelor's(43); graduate/professional
(44–46). Missing/out-of-universe values are reported explicitly. Source
population and target exclusions, including armed-forces household
members, must be fixed with ED2's universe crosswalk before fitting.

[frozen] ED1 is **fit conformance**, admitting only the fitted schedule.
It does not establish a population projection claim. [open] Repeated
cross-sections alone do not identify individual transition probabilities;
ED1 must register its synthetic-cohort/panel construction and constraints.
Attainment cannot fall, shares sum to one, attainment is absorbing after 35,
and fixed seeds reproduce draws (design§6).

[proposed tolerance] Each fitted training share differs by at most0.005
from its training target. If the target's simultaneous uncertainty bound
is narrower, conformance must also respect that bound. The registered
family includes every reported age/cohort/sex/category cell; sparse cells
are pooled before fitting under a fixed rule and never deleted after
outcomes. The exact pooling hierarchy is [open].

### 4.4 Dates, exposure, uncertainty and conditions

| Input | Reference/interview date | Publication-availability date | Status |
|---|---|---|---|
| ASEC 2023 | Current demographics at 2023 interview; income 2022; official documentation labels March 2023 | Initial raw release date open; processed mirror18 September 2026 | [open: exact collection and raw-release dates] |
| ASEC 2024 | Current demographics at 2024 interview; income 2023; March 2024 supplement | Initial raw release date open; processed mirror18 September 2026 | [open] |
| ASEC 2025 | Current demographics at 2025 interview; income 2024; March 2025 supplement | ZIP-member timestamp28 July 2025 recorded by preserved attempt is **not** an initial release date; processed mirror18 September 2026 | [open] |
| ASEC 2026 | Current demographics at 2026 interview; income 2025; March 2026 supplement | Initial raw release date open; processed file27 September 2026 | [open] |
| All Microcosm code declarations | Code snapshot24 October 2026,14:13:24 UTC | Same immutable commit | [frozen] |

The four Census technical-documentation pages were retrieved 24 October 2026;
their shared last-revised date2 September 2026 does not establish original
microdata availability. ED1's training cutoff and prediction boundary
remain [open] until its selected inputs and these dates are pinned.
There is no ED1 unused prediction holdout: training-table reproduction is
conformance. ED2's holdout is separately registered.

[frozen exposure] The approved design§11 records no Census attainment
values. The preserved attempt recorded public parent-pointer aggregates;
this continuation used documentation/code, and read attainment-table
string labels/notes without numeric estimate cells. The separate
search-snippet incident is recorded in this audit's exposure section and
the manifest; it supplied no ED attainment values.

[proposed uncertainty] Use simultaneous 95% bounds with Bonferroni over
the registered family. Resampling must preserve CPS survey design,
household/family clusters and rotation-panel overlap across pooled years;
replicate weights are used where available. Monte Carlo share error must
be below 0.0005, one tenth of the 0.005 conformance tolerance. The pass
conjunction requires every critical cell to conform and every ED invariant
to pass; inadequate precision is inconclusive. The named procedure is `ED1-Fit-Conformance-v1`: deterministic training
share inequalities and the registered invariants. Its 0.005 limit is
separate from ED2's 0.02 prediction limit; the script's ED2 power output
does not establish power for ED1's tighter conformance tolerance.

[proposed suppression] Public cell output requires at least 100 unweighted
persons, the SSA minimum cited in section 1.5; stricter applicable rules
prevail. Parent-link missingness is reported under the same rule.
`SOURCE_UNAVAILABLE` applies to an unavailable selected source;
`EXPOSURE_UNRESOLVED` to an unresolved intended holdout;
`GATE_FAIL_OR_REGRESSION_FAIL` to failed conformance/invariants;
`SMALL_CELL_DISCLOSURE` blocks an unsuppressed small-cell artifact.
`FRAME_ATTRIBUTE_MISSING` remains triggered downstream until a checked
frame supplies attainment. No ED1 projection admission is implied.

## 5. ED2: the education gate

### 5.1 Source releases and exact table structures

[frozen] The 2024 releases below are definitions/calibration candidates,
not automatically unused prediction targets. All were retrieved 24 October
2026. Local file names use the source directory in section 4.1. Each
listed SHA-256 was verified against the saved file. The release pages
below support the table locators and publication-history claims in
sections 5.1–5.2. Future release selection remains [open].

| Release | Vintage/locator | URL | Local file | SHA-256 | Access date | What this note relies on |
|---|---|---|---|---|---|---|
| Census CPS detailed Table 1, *Educational Attainment of the Population18 Years and Over, by Age, Sex, Race, and Hispanic Origin:2024* | 2024 ASEC; page revised 28 August 2025; labels row6; sex/ages rows22–51 | https://www2.census.gov/programs-surveys/demo/tables/educational-attainment/2024/cps-detailed-tables/attain01_2024_1.xlsx | `census_attain01_2024_1.xlsx` | `3aea3a9f9ded5e94be62c9a6444f9846aeddd50304dc357c83a9fc258702e385` | 2026-10-24 | Detailed attainment categories, joint age/sex structure and footnote in section 5.1. |
| CPS detailed Table 2, *…25 Years and Over, by Selected Characteristics:2024* | 2024 ASEC; labels row6; source A78 | https://www2.census.gov/programs-surveys/demo/tables/educational-attainment/2024/cps-detailed-tables/attain02_2024_1.xlsx | `census_attain02_2024_1.xlsx` | `9e866e557eefb40254cd18373d5f7b1198860c9dfedc69f2e77980b065b15d6c` | 2026-10-24 | Selected-characteristic categories and age-cell limitations in section 5.1. |
| CPS detailed Table 3, *Detailed Years of School Completed by People25 Years and Over by Sex, Age Groups, Race and Hispanic Origin:2024* | 2024 ASEC; header rows 4–5; source A54 | https://www2.census.gov/programs-surveys/demo/tables/educational-attainment/2024/cps-detailed-tables/attain03_2024.xlsx | `census_attain03_2024.xlsx` | `88ee5269267e5a84e7cf6f006895e94d2853fd4c428e82e79b5bf786944df9e2` | 2026-10-24 | Separate marginal structures and category definitions in section 5.1. |
| CPS historical A-1, *Years of School Completed by People25 Years and Over, by Age and Sex:Selected Years1940 to2024* | Page revised 14 October 2026; column labels4–6; comparability noteA850; source A855 | https://www2.census.gov/programs-surveys/demo/tables/educational-attainment/time-series/cps-historical-time-series/taba-1.xlsx | `census_taba-1.xlsx` | `252125cdb35edbb0c4e65b2f5f8fdd00b11e8abcc7f93cc7991613c41d4ab472` | 2026-10-24 | Historical category definitions and comparability note in section 5.1. |
| CPS historical A-2, *Percent…Completed High School or College…Selected Years1940 to2024* | Page revised 14 October 2026; labels4–5; race noteA284; question-change noteA286; source A291 | https://www2.census.gov/programs-surveys/demo/tables/educational-attainment/time-series/cps-historical-time-series/taba-2.xlsx | `census_taba-2.xlsx` | `1491f7f9676436aa72d8b7ea5a478a4273227256aaf8702cca313c7269a64341` | 2026-10-24 | Historical category/race definitions and question-change note in section 5.1. |
| ACS 2024 one-year B15001 variable metadata, *Sex by Age by Educational Attainment for the Population18 Years and Over* | Metadata only; age25–34 by sex; group-quarters-inclusive universe | https://api.census.gov/data/2024/acs/acs1/groups/B15001.json | `census_acs2024_acs1_groups_B15001.json` | `0b95a6175d511898b81b9d9bf89f5b61e1d47a09620008e8056c8033e00b3132` | 2026-10-24 | Attainment/age/sex metadata and universe crosswalk in sections 5.1 and 5.4; no estimate cells. |
| Census educational-attainment tables index | Release link list | https://www.census.gov/topics/education/educational-attainment/data/tables.html | `census_edu_tables_index.html` | `89a6dde3d7825c9929c95e3d606d9175aa41a3f8a1e16ac47ae196eeb40b2fd8` | 2026-10-24 | Located CPS detailed and historical table releases in section 5.1. |
| Census Educational Attainment in the United States: 2024 release page | Detailed-table release page | https://www.census.gov/data/tables/2024/demo/educational-attainment/cps-detailed-tables.html | `census_edu_cps_detailed_2024.html` | `5276039ae45f96b821a4d420e5d1bffb469ba824d1451da0196e604e85c25e42` | 2026-10-24 | Detailed-table links and page revision date in section 5.1. |
| Census educational-attainment historical time-series release page | Historical-table release page | https://www.census.gov/data/tables/time-series/demo/educational-attainment/cps-historical-time-series.html | `census_edu_historical.html` | `cd2c9cf05b2c39760dd28da9c92b4e517418e5e03c7317d10c12c284350cfe76` | 2026-10-24 | Historical-table links and page revision date in section 5.1. |
| Census ACS 2024 New and Notable | Dated release entries | https://www.census.gov/programs-surveys/acs/news/data-releases/2024/release.html | `ed_census_acs2024_release.html` | `45ea9e6e9cc083be269caa9faf4eb16c91a1c4dcf650f7ea836ab21b2e2174b3` | 2026-10-24 | One-year estimates and PUMS publication dates in section 5.2. |
| Census ACS 2025 Data Release Schedule | Release schedule and update date | https://www.census.gov/programs-surveys/acs/news/data-releases/2025/release-schedule.html | `ed_census_acs2025_release_schedule.html` | `87f1eb5b32713ed9313c2368c51bd298e709bd2c5413bdf5fffdacbf7b37f95f` | 2026-10-24 | Scheduled detailed-table release and unresolved PUMS release date in section 5.2. |
| Census ACS 2025 New and Notable | Dated documentation entry | https://www.census.gov/programs-surveys/acs/news/data-releases/2025/release.html | `ed_census_acs2025_release.html` | `b47a6ed9ae9564de6e4696e3bd49f00d1216df21263f661fdd19ea8b124cedbf` | 2026-10-24 | Table-shell/documentation availability in section 5.2. |

[frozen categories] Table 1 separates15 attainment categories, including
occupational/academic associate and bachelor's/master's/professional/
doctorate; its11th-grade column includes12th grade without diploma
(footnoteA53). It provides sex × 25–29 and sex × 30–34. Table 2 has nine
categories and selected characteristics for 25+, without the required
age-specific cells. Table 3 distinguishes GED/no-diploma and college years,
but **sex, age and race are separate marginal columns**, not a joint
25–34×sex table. A-1 aggregates elementary0–4/5–8, high-school1–3/4,
college1–3/4+; since 1992 these refer to credentials as its note explains.
A-2 reports high-school-or-more and bachelor's-or-more, including25–29;
from 2003 its White/Black/Asian columns denote race alone, with separate
alone-or-in-combination columns. These historical tables cannot identify
all five proposed categories for a modern fine-cell gate.

B15001 has seven categories: below 9th;9th–12th/no diploma; high-school/
equivalent; some college/no degree; associate; bachelor's; graduate/
professional. Combine its first two and its some-college/associate cells
to match ED1's five categories. Its25–34 band does not identify separate
25–29/30–34 or single-year birth cohorts.

### 5.2 Dates, availability, holdout and prediction origin

[frozen] ACS 2024 one-year estimates were published 11 September 2025;
its one-year PUMS was published 4 December 2025 (Census 2024 *New and
Notable*, dated entries). Its observations refer to interviews throughout
calendar 2024, rather than one ASEC interview date.

[frozen] Census's *2025 Data Release Schedule*, updated13 October 2026,
schedules 2025 ACS one-year detailed tables for **29 October 2026**;
2025 one-year PUMS is **TBD**. The supporting *New and Notable* page says
table shells/documentation were released22 October 2026. This establishes
why 2025 estimates were unavailable on 24 October 2026; a 404 alone would
not establish a publication history. Both pages' retrieved bytes are
pinned in the manifest.

[proposed partition] If ED1 permits every pinned CPS year, survey 2026 is
the latest possible training year and CPS 2027 the earliest later survey
year. If ED1 selects only older years, recompute that boundary from the
registered selection. Microcosm's reviewed ACS spine references2024;
ACS 2025 is later in reference time, but source overlap, frame calibration
and exposure still require audit. In particular a target **before** the
prediction origin cannot establish prospective prediction merely because
its publication is later. A 2026 origin must predict a post-origin
reference period. ACS 2025 can at most support a registered retrospective
or delayed-measurement check of an earlier origin.

[open] Before ED2 registers, pin the exact frame release, its source
reference/interview/availability dates, ED1 fit cutoff, origin date,
prediction dates, target release and availability date, all frame
calibration targets, cohort convention, and a target-value exposure ledger.
No current label search establishes an unused holdout. An already
published release may remain unused only with an explicit exposure and
non-use audit; a future release after registration provides a cleaner
prospective target. Exact-year birth cohorts require public microdata and
an explicit age/birthday convention; the published tables support
age-defined cohort bands only.

### 5.3 OACT, PWBM and definitions-only inputs

[frozen search scope; open finding] No dedicated attainment-projection
release was located in the permitted OACT study/note catalogs inspected
by the preserved attempt. Absence of a title is not proof that OACT
publishes none. The OACT publication question remains open. Census is the
**proposed** ED2 primary while this is unresolved. PWBM is located only at
S0.2. Any Urban education-process definition reaches ED2 through a
validation lane's cleared definitions-only extract; this audit opens no
Urban material.

### 5.4 Population, estimand and critical family

[proposed] ED2 estimates each of ED1's five attainment shares at 25–34 by
sex and registered age-defined birth cohort. The 0.02 absolute-share
limit is [frozen] from design§5.3 and is never loosened. A full family of
ten single-year cohorts × two sexes× five categories has 100 cells and needs
a microdata target; it cannot be recovered from the listed published
tables. A pre-registered grouped-cohort scope gives 20 cells using CPS
Table 1's25–29/30–34×sex; pooling25–34 gives 10 cells, with correspondingly
narrower admission. Scope and pooling are chosen before outcomes, with
power recomputed; failed cells cannot be removed to obtain a pass.

[open universe crosswalk] The CPS tables' heading says civilian
noninstitutionalized population, and their notes explicitly add armed
forces living off post or with families on post (Table 1 A52; Table 2 A72;
Table 3 A51; A-1 A848; A-2 A283). ACS B15001 includes group quarters.
Restricting ACS to household records alone does not establish an exact
CPS match. Freeze institutional/noninstitutional group quarters,
armed-forces status and residence rules before scoring. A PUMS-based
matched-universe target is proposed; the published B15001 universe is a
separately labeled sensitivity. No unmatched-universe cell admits an
ED2 claim.

[proposed informativeness] Primary cohorts must have been24 or younger
at the origin, so schooling transitions can affect the outcome. Under
annual-age arithmetic, for every member of 25–29 in target yearT to meet
that rule at originF requiresT≥F+5;30–34 requiresT≥F+10. WithF=2026,
that is2031 and 2036. A nearer target can include only the qualifying
single-year cohorts, with its family registered in advance. A cell whose
attainment is fixed before origin tests initial conditions, not ED1's
transitions. Retrospective alternatives require older frames and training
sources under their own registration and exposure audit.

### 5.5 Uncertainty, power, suppression and pass conjunction

[proposed procedure] Use the invented-data
`simulate_ed2_normal_family` / `ed2_analytic_grid` procedure in `scripts/s0_1_power.py`, with the
registered family size, target effective size, model/frame effective
size, assumed category shares and clustering/design effects stated. Power
is the probability of the full equivalence-pass conjunction when the
model is correct; require at least 0.90. The grid and resulting thresholds
are in section 6. Do not treat an effectively infinite target sample as a
verified description of ACS.

[proposed uncertainty] Simultaneous95% bounds use Bonferroni over all
critical cells. Resampling preserves household/family clustering and the
survey design on both model-frame and target sides; CPS pooled-year
rotation overlap and any frame-target overlap enter covariance rather
than an independence assumption. Use the survey's replicate procedure
where available. ACS published 90% margins divided by 1.645 recover
marginal standard errors, but category aggregation requires covariance or
replicates; summing marginal variances silently is not allowed. Include
fit-parameter uncertainty. Monte Carlo share error must be below 0.002,
one tenth of the tolerance, with replicate count registered in advance.
Insufficient precision is inconclusive, never a pass.

[frozen executable scope] The invented independent-household sampler
uses a finite-sample Hoeffding bound, with Bonferroni adjustment across
all categories (`ed2_cluster_half_width`). Conditional on weights and
household sizes, each household's contribution lies in an interval whose
length is its normalized total weight. With S the sum of squared lengths
across the independent model and target samples, the half-width is
`sqrt(S * log(2m/alpha) / 2)`. Hoeffding's inequality bounds each
category's miss probability by `alpha/m`; the union bound covers all m
categories. This holds for sparse and zero-count categories and arbitrary
dependence within each household. Projection replicates do not create
independent households. The separate projection-MC veto remains binding.
The sampler makes weights independent of attainment and samples independent
households on each side. It cannot establish coverage for overlapping
complex surveys. Those require their registered design-specific bound;
unsupported precision returns inconclusive. Normal-grid effective-size
thresholds remain conditional planning approximations, not thresholds
for this more conservative finite-sample procedure.

[proposed conjunction] Every critical cell's simultaneous bound must lie
inside [−0.02,+0.02], all source/date/universe requirements must be met,
and required invariants/regressions must pass. A wholly outside bound is
a failure; remaining nonpassing bounds are inconclusive. No seed
selection, dropping cells or tolerance relief follows an outcome.

[proposed suppression] Publish a cell only with at least 100 unweighted
persons on both sample sides, meeting SSA's cited minimum(section 1.5),
with complementary suppression where needed. This does not substitute for
power; design effects and category denominators still matter.

### 5.6 Exposure and named conditions

[frozen exposure] The audit read the listed Census spreadsheet labels
and notes without numeric estimate cells. No value from a prospective ED2
target was used to select this tolerance. The preserved attempt's public
parent-link summaries are ED1 exposure; they do not establish an unused
ED2 holdout. The separate OACT search-snippet incident and prior lane
exposure remain recorded in the general exposure ledger.

- `FRAME_ATTRIBUTE_MISSING` remains triggered for the checked Microcosm
  releases: by the ED kill criterion ED2 waits for attainment, and cannot
  run on imputed starting education without its own registration.
- `SOURCE_UNAVAILABLE`/`EXPOSURE_UNRESOLVED` remain open blockers until
  target releases, all availability dates, the frame/universe crosswalk
  and an unused holdout are established.
- `WEAK_POWER_OR_VACUITY` applies to any registered family whose power is
  below 0.90, and to a near-term claim supported only by already-fixed
  attainment. Section 6 separates hypothetical grid findings from facts
  about an actual frame or target.
- `SMALL_CELL_DISCLOSURE` blocks any unsuppressed small-cell artifact;
  `GATE_FAIL_OR_REGRESSION_FAIL` blocks admission when a required gate
  or regression fails. Unsupported or failed cells remain reported and
  cannot be dropped after the result.

## 6. Power on invented data

### 6.1 Frozen procedure and declared assumptions

**[proposed test protocol; frozen executable output]**
`S01-Bonferroni-Equivalence-Grid-v2`, script schema `s0_1_power.v3`,
seed 20261024. Reproduce with:

```sh
.venv/bin/python scripts/s0_1_power.py --sims 300000 \
  --seed 20261024 --out docs/design/s0_1_power_results.json
```

Every population, group share and survey structure is invented. The only
optional external numerical input is the permitted repository OACT TR
2026 `q`, reported as descriptive sex/age-band means, never as a
PSID count. `--no-anchors` omits it. SM2/ED1 are conformance procedures
and SM4 is report-only; none acquires a predictive power claim from this
script. The simulated scientific pass conjunctions are SM3 and ED2.

For cell estimate `x`, known planning SE `s` and family size `m`, pass
requires `|x| + z*s ≤ tolerance`, with
`z = Φ⁻¹(1 − .05/(2m))`. Under assumed true error `δ`, the marginal
pass probability is the normal interval probability between
`(-tolerance-δ)/s+z` and `(tolerance-δ)/s-z`, or zero for an empty
interval. The registered sufficient family-power calculation uses
`max(0, 1 − Σ(1 − p_cell))`: a union bound valid under arbitrary cell
dependence **within the declared marginal normal model**. Multiplying
marginal probabilities is reported only as an independence approximation.
Bonferroni coverage and a lower bound on conjunction power are distinct
calculations.

For SM3, the planning variance is
`deff × (1/D_cell − 1/D_cohort)`. The cohort-wide denominator includes
10% invented unclassified deaths. The equal classified cell shares are
0.9/20 for earnings and 0.9/16 for education/race; they are assumptions,
not actual group death shares. Raw-person screening uses
`effective deaths = assumed persons × assumed window death risk / deff`.
Finite Bernoulli risks, unequal weights, shared person histories,
stratification, fitted-parameter error and real family covariance can
change this approximation. Full-family normal simulation preserves the
shared denominator; separate clustered Bernoulli/weighted-population and
Rao–Wu diagnostics exercise the survey estimators without certifying the
actual design's precision.

**[frozen assumed grid]** Persons per classified sex/band/group cell:
100, 250, 500, 1,000, 2,500, 5,000, 10,000, 25,000, 50,000, 100,000,
250,000, 500,000. Window death probabilities: .02, .05, .10, .25.
Design effects: 1, 1.5, 2, 4. The Cartesian person/risk/design-effect
grid evaluates true error zero. Separate effective-death threshold rows
cover true absolute log-error bounds 0 and .05. All grid rows, flags and
minima are in the invented results artifact. Very large rows are diagnostic extensions outside the
public sample envelope, not plausible counts for this cohort.

Public structural context comes from PSID's *Main Interview User Manual:
Release 2013*, July 2013, Table 1 (PDF p. 18), which reports 24,661
individuals and 8,907 families in 2011. These are published documentation
totals, not eligible group counts computed from data. The source was
located through the web tool; raw PDF byte retrieval remains open after
HTTP 403 (manifest). The grid's envelope flag merely tests whether
classified persons summed over its independent cells exceed that public
whole-sample total. Actual persons may contribute histories to both age
bands; this flag is context, not an empirical variance bound. No PSID
death tally from a codebook or earlier run is used.

### 6.2 SM3 thresholds and weak-power findings

Smallest integer **effective deaths per cell** for the conservative 0.90
family-power guarantee under those assumptions (not exact minima for an
unknown real covariance):

| Dimension | Cells | True error 0 | Absolute log error ≤.05 | 52-cell sensitivity, error 0 |
|---|---:|---:|---:|---:|
| Lifetime earnings | 20 | 1,662 | 3,716 | 2,005 |
| Education | 16 | 1,564 | 3,483 | 1,982 |
| Race and Hispanic origin | 16 | 1,564 | 3,483 | 1,982 |

For design effect 1, the first assumed person-grid crossing is the same
for all three dimensions because the grid is discrete:

| Assumed window death probability | Smallest passing grid persons per cell |
|---|---:|
| .02 | 100,000 |
| .05 | 50,000 |
| .10 | 25,000 |
| .25 | 10,000 |

The analytic sufficient raw-person threshold is
`ceil(min_sufficient_effective_deaths × deff / risk)`; all 48
rate/design-effect/dimension minima are recorded in the JSON. At risk
.25 and design effect 1, these integer thresholds are 6,648 for earnings
and 6,256 for either four-category dimension, below the discrete grid's
first passing 10,000. These describe invented populations only.

**[frozen conditional finding] `WEAK_POWER_OR_VACUITY`** applies to all
screening rows that cannot achieve the registered 0.90 guarantee. No
screened row within the public independent-cell person envelope reaches
0.90 in this approximation; the successful rows lie outside it. This is
not a proof that every possible real design or prospective rescoping has
low power. Actual deaths, risk exposure, unequal category shares,
clustering and the covariance with the overall denominator remain open.
The SM kill criterion is stated in section 1.5; no source pair with an
unused holdout and actual 0.90 precision is established here.

### 6.3 ED2 thresholds and target sampling error

The invented five category shares are (.08, .26, .26, .26, .14).
The binding planning binomial variance is `.26×.74`. Each sex/cohort
sample contributes all five shares; “persons per cell” below means the
whole sex/cohort denominator, not a separate sample for each category.
Use `p(1-p)×(1/n_model_eff + 1/n_target_eff)` with independent sample
sides for this grid. Real sample overlap/covariance and parameter
uncertainty require registration. Negligible target error is an
assumption, not an assertion about ACS.

| Scope | Bonferroni cells | Negligible target error | Target effective n=100,000 | Target effective n=20,000 | Target effective n=5,000 |
|---|---:|---:|---:|---:|---:|
| Single-cohort × sex (primary) | 100 | 22,054 | 28,294 | No finite sufficient n | No finite sufficient n |
| Five-year age/cohort bands × sex | 20 | 16,351 | 19,547 | 89,613 | No finite sufficient n |
| Pooled 25–34 × sex | 10 | 13,938 | 16,195 | 45,975 | No finite sufficient n |

For the primary 100-cell family with true share error .005, the sufficient
model denominators rise to 36,922 with negligible target error, or
58,534 with target effective n=100,000. Full rows are in the artifact.
A “no finite sufficient n” entry triggers `WEAK_POWER_OR_VACUITY` for
this conservative procedure: target noise alone prevents its guarantee.
It is not a sharp theorem about an unspecified target covariance.
Actual frame/target effective sizes and shares were not measured. The
100-cell source microdata, dated unused holdout, starting education,
universe match and informativeness requirements remain open (section 5).

### 6.4 Simulation, Monte Carlo precision and tests

Full-family normal simulations use 300,000 repetitions per point and
fixed seeds. Worst-case 95% Monte Carlo half-width is .001789, below
.002 (one tenth of ED2's tolerance) and below the SM3 requirement.
A simulated power claim additionally requires the Wilson 95% lower
bound ≥.90; a point estimate alone cannot pass that criterion.

| Invented complete family | Planning count | Simulated pass probability | 95% Monte Carlo lower bound |
|---|---:|---:|---:|
| sm3_16_cells_deaths_1564 | 1,564 effective deaths/cell | 0.905297 | 0.904244 |
| sm3_20_cells_deaths_1662 | 1,662 effective deaths/cell | 0.905163 | 0.904110 |
| ed2_100_cells_model_n_28294 | 28,294 model / 100,000 target persons | 0.941877 | 0.941034 |

Clustered Bernoulli and family/survey bootstrap diagnostics use only 40
outer repetitions. They are explicitly insufficient for a 0.90 power
claim, and their reach flags are false. Bootstrap endpoint and projected
share Monte Carlo errors must be checked in a later registered run;
illustrative replicate-count formulas alone do not establish that error.
The synthetic normal grid does not substitute for those checks.

`tests/s0_1/` contains Hypothesis and example checks of fixed-seed
reproducibility, sample-size and equivalence-effect monotonicity, normal
boundary pass rates, simultaneous coverage, shared-denominator/unclassified
handling, the conservative threshold's minimality, survey-cluster
refusals, Monte Carlo precision and malformed-input refusal. For continuous
normal estimates with known positive standard errors, the two-sided 95%
rule has pass probability at most `.05/(2m)` at an individual equivalence
boundary, approaching it in precise examples; family false admissions
are conservative under that normal model.

That nominal boundary-rate claim does not apply to sparse discrete
estimates or zero-width bounds. The low-level closed-tolerance classifier
still accepts exact endpoint bounds, but ED2 no longer constructs
zero-width plug-in Wald bounds for empty categories. Its household
Hoeffding bounds have finite-sample simultaneous coverage under the
invented design described in section 5.5. Tests sum exact binomial
sampling probabilities, rerun the review's sparse/outside-tolerance
fixture, and check the minimized registered family and projection veto.
ED2's low-level variance diagnostic refuses fewer than two realized
clusters; the simulation catches only `UnestimableRealization` and counts
that trial once as inconclusive, without retry or redraw. Summary counts
record every trial explicitly as pass, fail or inconclusive.

SM3's cluster-linearized and bootstrap intervals remain asymptotic
diagnostics. A tiny accepted invented sample does not meet nominal
coverage: the executed review-fix check used four clusters, two equally
likely groups, risk .5 and log misfits (.1, -.1); seed 9 minimizes an
uncovered diagnostic pass to one trial. The repeated check's diagnostic
coverage is recorded in the retained fix scratch. No finite-sample
coverage bound for that full clustered SM3 domain is established here.
`simulate_sm3_family` therefore retains raw outcome counts and coverage
under explicitly diagnostic keys and returns every gate trial as
inconclusive. The separate known-SE normal experiment keeps its
conditional normal-model coverage. Hypothesis checks exact accounting,
deterministic seeds, accepted sparse/clustered inputs without aborts, and
supported coverage or inconclusive treatment of unsupported precision.
The accepted input domain also includes configurations outside the
invented sampler's supported numerical/computation envelope. Those are
counted as inconclusive before sampling. Executed endpoint checks found
weight-CV overflow at `1e155` (but not `1e154`) and an unsupported Poisson
mean at `1e20`, minimized to two categories, ten persons and one trial.
The SM3 weight diagnostic had the same overflow with four clusters.
Property tests include these finite endpoints, underflowing Dirichlet
parameters and a draw budget beyond `MAX_INVENTED_PERSON_DRAWS`.
Malformed specifications still raise at validation. These refusals do not
change any tolerance or turn unavailable precision into a failure.
“Increasing effect” means greater separation from the inequivalence
boundary toward correctness; increasing model error lowers pass power.

## 7. Files read, exposure and continuation provenance

**[frozen] Continuation boundary.** Work resumes from `2195258c00e67e27dbc7946cc82975678e118f11` with the preserved working files
represented by salvage ref
`refs/subfleet-salvage/mgf-s0-1-source-audit-20261024-20261024T151511Z-a1`.
That ref was inspected by metadata/stat only and is not an ancestor to
merge or push. The original attempt's downloads and source-access claims
remain in the manifest. This continuation corrects their conclusions; it
does not assert that it can independently reconstruct the earlier
session's complete read history.

**Direct local reads outside this repository in this continuation:**

- `/Users/maxghenis/microcosm-launch-evidence/dynasim-parity-20260909/RESTRICTED-FILES.md`, read first, in full in bounded chunks.
- `/Users/maxghenis/microcosm-launch-evidence/dynasim-parity-20260909/merge-watchers/recount-tiers.py`, read and executed only for tier collection with an empty data root.

Public remote documentation and pinned Microcosm source code are listed
file by file in `.s0_1-sources/MANIFEST.md`; downloads and scratch stay
inside this workspace. The Python interpreter/dependencies reached through
`.venv` are runtime tools, not evidence sources. The original attempt's
saved draft also reported reading repository/parent-folder `CLAUDE.md`
files and Microcosm code, without a complete absolute local-path ledger;
that inherited provenance gap remains **[open]**. No other session's
transcripts, restricted scratch folders or job logs were consulted to fill
it.

**Repository evidence read:** approved design at `2c19f5b6`, required
sections; SM1 design and specification at `0c226e3f`; the code locators
cited in each gate, including `cohorts/group_attributes.py`,
`cohorts/psid2010.py`, `data/psid.py`, `data/deaths.py`,
`data/life_table.py`, `data/group_attributes_psid.py`,
`baselines/base.py`, `baselines/tr2026_intermediate.py`,
`estimates/group_breakdown.py`, `gates.yaml:5324–5410`, the captured
MINT8 guide's sample-size restriction, and tier-policy code/manifests.
`data/deaths.py` was read with digits masked in this continuation because
its docstring embeds codebook tallies. The preserved draft had copied
those tallies into a feasibility argument; continuation reads of the draft and power script displayed
that legacy text before replacement, and an initial test read the inherited
results artifact containing it. Permitted design/plan reads also displayed
historical sample-size summaries; none of those values informed the revised grid. No such tally is retained in the
final record, script, tests or power artifact, and none informed the
revised power grid. No PSID data record was opened or statistic computed.
Public sample-size documentation is identified separately as a grid
envelope, never as an eligible group count.

**Historical build validation and version-control status (2026-10-24).**
The original invented-data
suite passed: 74 tests (`.venv/bin/python -m pytest -p no:cacheprovider
tests/s0_1 -q`, 62.64 seconds), with the empty-root environment exported.
Black (79 columns) and Ruff passed. The source-manifest hash check matched
61 downloaded files. The full-collection policy check passed: 1 passed, 2 skipped,
24,692 deselected (454.64 seconds). The manifest records 18,162 unit,
4,253 artifact, 1,450 integration, 520 legacy and 308 oracle tests,
24,693 total. The prescribed five-pass recount completed successfully
and reproduced every count: unit 18,162; artifact 4,253; integration 1,450;
legacy 520; oracle 308. Every pass collected the full 24,693-item inventory.
Its five identical real pytest commands were dispatched with at
most four concurrent processes; the unchanged external helper then parsed
those captured `CompletedProcess` outputs and wrote the manifests. No
collection was replaced by inferred counts or a subset. Slow repeated path resolution was cached only while collection
hooks ran, using the untracked `s0_1_collection_cache` plugin; `Path.resolve`
was restored before executing the selected test. Classification rules and
source files were unchanged; collection was complete, not subsetted. No `src/`, shared engine, gate
or committed run file was changed. The sandbox refused `git hash-object
-w` with “Operation not permitted”, so ordered commits, push and draft PR
could not be created. Branch `mgf-s0-1-source-audit-20261024` remains at
`2195258c00e67e27dbc7946cc82975678e118f11`; the lane session must commit the
five gate sections in SM3/SM2/SM4/ED1/ED2 order, then power/tests, then
housekeeping, using the requested co-author footer.

**Round-2 fix verification (2026-10-25).** The required initial
checksum check matched all seven deliverables. The complete named suite
passed: 99 tests (`.venv/bin/python -m pytest -p no:cacheprovider
tests/s0_1 -x -q`, 150.76 seconds). After refining the small-sample property
to allow a rare statistical failure while forbidding imprecise passes,
its focused rerun passed: 1 passed, 14 deselected. The five serial
`tests/s0_1 --collect-only -q -m <tier>` collections give 99 unit tests and
zero in artifact, integration_psid, reproduction_legacy and
oracle_policyengine. Current arithmetic is base unit 18,088 + 99 = 18,187
and base total 24,619 + 99 = 24,718; other tiers remain unchanged.
Black's 79-column check and Ruff passed on all changed Python files.
The current fix did not run full collection, the recount helper or the
full-collection tier assertion. The preceding full-collection results
are historical. All pytest commands used the empty data root.

**Current power artifact (2026-10-25).** The calculation completed in
501.314 seconds using the script's command with its default seed and
simulation count:

```sh
.venv/bin/python scripts/s0_1_power.py --no-anchors --out .fix-scratch/r2/results-no-anchors.json
```

The deadline was 3,600 seconds. The changed top-level fields are
`schema_version`, `procedure`, `validation` and `clustered_validation`.
Analytic planning sections remain unchanged. New summary fields record
explicit outcome counts. SM3 cluster results now expose their raw
coverage/decisions only as diagnostics and count all gate trials as
inconclusive; ED2 uses household Hoeffding bounds. The existing
`tr2026_band_q` section was preserved exactly from the preceding artifact.
The anchor branch was not executed: `data/tr2026.py:_data` verifies and
opens excluded `data/external/` inputs. No fresh anchor verification or
whole-input rerun is claimed. Final script/test/artifact digests below
replace the stale pre-fix digests.

**Round-2 provenance.** The read ledger is `.fix-scratch/reads-r2.md`;
retained helpers, reproductions, exact commands, output and deadlines are
in `.fix-scratch/r2/`. All 33 permitted source checksums used for the
metadata/locator fix matched the archived manifest. The excluded CBO
capture retains only its historical manifest pin. This job, clone and
scratch remain exposed. Nothing was committed, pushed or posted.

**Frozen numerical environment and final artifacts (2026-10-25).** Python 3.14.7, numpy 2.5.4, scipy 1.18.1, hypothesis 6.170.9, pytest 9.1.1. SHA-256:

- `scripts/s0_1_power.py`: `018017fdd8e6904fbdcb423d92415effee4e488ead3faae6334bca253f221f1f`.
- `tests/s0_1/__init__.py`: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- `tests/s0_1/test_s0_1_power.py`: `0b8ec8ba6a54b62b799ac160d5ac080df78600e8a1a42a9708bad254074e99d3`.
- `tests/s0_1/test_s0_1_invariants.py`: `76b55b98888daf3664fb8297a8ad44cd2bc6e099146cfbd172b1e410cbf37003`.
- `docs/design/s0_1_power_results.json`: `58569c9667c1c1af0e5d5a2fcc0d0e4cd1ed8002fb44d5fe01370f60f1ac74f3`.

**Artifact metadata.** Section 1.3 records the mortality and m6 files.
Two further previously cited artifacts were checked by digest, addition
commit and top-level keys only:

| Path | SHA-256 | Addition commit | Top-level keys |
|---|---|---|---|
| `runs/replication_boomers2004_uniform_cut_v1.json` | `48fb6cb108b09e19ed10c32586bd1b0d9521ec7746f693ba0241963ac24a4de3` | `29d7a3ccceef5128d040626a18815d70492c7e35` | `checks`, `cohort_provenance`, `comparator_column`, `comparator_seal_opened_before_commit`, `data_provenance`, `f17_diagnostics`, `header`, `headline`, `input_checks`, `labels`, `named_deltas`, `parameters`, `pending_decisions`, `psid_files_sha256`, `publishes_regardless`, `registration_pointer`, `report_rows_not_computed`, `rows`, `run`, `schema_version`, `specification`, `statistic_id` |
| `runs/replication_mermin_rows_v1.json` | `c55c2f35856eb56c6ead6428dbd5085a5910b3ee651a15c4ae22b45f51656100` | `bbf8dc2459de827f360a1bd86eaf437d1b9b958f` | `anchor_provenance`, `cola_minus_0_4pp`, `conventions`, `elapsed_seconds`, `nra_raise_to_70`, `per_seed`, `program_design_issue`, `purpose`, `real_data_only`, `registered_expectation`, `registration`, `registration_pointer`, `reported_not_gated`, `revision_pins`, `run`, `schema_version`, `study_population`, `what_is_tested` |

**Exposure incidents and limits.** The inherited manifest says the
original attempt read CBO 49659 only with digits masked and stopped at
slides that reproduce excluded financing material. This continuation
does not reopen those mixed slides. During the ED source check, a scoped
SSA attainment search nevertheless returned expanded financing/depletion
snippets from excluded SSA pages. That subagent stopped; it opened no
result page, captured no snippet value and used none in a choice or
calculation. Exact source URLs and the incident are recorded in the
manifest. The exposed subagent must not be reused for a blinded financing
or affected comparison role. No assertion of zero excluded material in
the whole job's context is made.

**No prohibited local file or data access.** This continuation opened
nothing on the restricted-file list other than the list itself, no
excluded repository file, no Urban/DYNASIM/PWBM material, no Trustees
financing page, no OACT solvency page, no MINT policy-option table, and no
PSID or HRS data file. It read no committed run-artifact value. Source
links or titles in permitted documents were not followed into exclusions.
Search-snippet exposure above is disclosed separately, not erased by this
statement. PSID use follows the project's data-access record.

## 8. What SM3's real-data step would need

This is the decision input for Q7; it makes no authorization recommendation.

- **Counts [open].** A separately authorized, registered structural step
  would supply persons at the boundary and entering each sex × age band,
  for every earnings/education/race category and unclassified status;
  weighted and unweighted person-years, deaths and model-expected deaths;
  weight sums/squares; survey strata, PSUs, families and repeated-person
  links; and the design-based covariance of every cell with the cohort
  overall ratio. Outcome-aware death/exposure counts must be segregated
  from any role claiming an unused holdout. A boundary-only stage can
  supply covariate/design counts and model-expected deaths first; actual
  deaths and follow-up exposure need their own registered disclosure and
  exposure protocol. This audit supplies none of those real counts.
- **Staged digests [open; complete loader ledgers required].** Keep the
  files read separate from the earnings reference years. The following
  inventory comes from loader code at `2195258c`; no staged file was
  opened or hashed. Freeze each actual relative filename and digest,
  reader/code version, retrieval/release date and report cutoff in a
  separately authorized ledger, including every ancillary input below.

  | Loader and input family | Files read and independent cutoffs |
  |---|---|
  | `cohorts/psid2010.load_psid2010_inputs:975–1072`: individual, death and disability readers | `ind2023er/IND2023ER.sps`, `IND2023ER.txt`, and `IND2023ER_formats.sas`. Anchor fields use 2011 by default (2009 is an alternative); disability status is capped at the anchor, while employment-code verification uses 2009 and 2011. Death records come from the cross-year product; the selected outcome window and release date need separate pins. |
  | Same cohort loader: family earnings and birth inference | The single non-formats `.sps` and single `.txt` selected in every `family/<wave>/` for annual waves 1968–1997 and biennial waves 1999–2023 (`data/family.py:52–55,622–640,813–822`). The demographic panel reads the individual product through the maximum selected wave. Default `birth_inference_max_wave=None` reads this entire family-wave set: its birth-inference cutoff is 2023, not the career's earnings cutoff. An explicit cap selects family earnings waves no later than that cap and cannot precede the anchor (`psid2010.py:984–1012`). |
  | Same cohort loader: Social Security readers | Family `.sps`/`.txt` for 2009, 2011 and 2013, plus the individual product and its SAS formats. `head_spouse_social_security_panel` and `read_individual_social_security` default to these report waves independently of the birth-inference cap; their income reference years are 2008, 2010 and 2012 (`data/social_security_income.py:84–86,392–418,597–626`). |
  | Same cohort loader: marriage-history reader | `mh85_23/MH85_23.sps` and `mh85_23/MH85_23.txt`; the whole marriage-history product is read with no report-year cutoff argument (`data/psid.py:68–70`, `data/marriage.py:94,250–255`). The latest-report fields and original release date must be audited separately; filtering episode dates at the opening year does not establish report availability. |
  | Same cohort loader: external claiming reference | The configured claiming-reference path, default `data/external/ssa_claim_ages_2014supplement.json`, and its reader/version pin (`psid2010.py:161–166,877–891,1013–1018`). This repository input lies outside the staged-data file-open bundle and needs its own ledger entry; it was not opened here. |
  | `cohorts/group_attributes.load_group_attribute_inputs:433–477`: individual and family reports | The individual `.sps`/`.txt`/`IND2023ER_formats.sas`, plus every family `.sps`/`.txt` for annual waves 1985–1997 and biennial waves 1999–2023. `data/group_attributes_psid.py:128–137,1542–1572,1614–1650` defines these ranges and readers. Later family waves 2013, 2015, 2017, 2019, 2021 and 2023 are mandatory in the shipped loader. |
  | Same group loader: documentation and formats | Each family-wave codebook PDF addressed by `family[wave].codebook.path` in the pinned value table; every `formats_sas.path` that the table pins; and each existing `family/<wave>/*_formats.sas` selected by the reader, including the documented 2021/2023 formats. `verify_codebook_pins:1671–1718` hashes those PDFs/formats and `read_family_items:1606–1642` reads available formats. The actual filenames must come from the authorized ledger, not a guess from this source-only inventory. |
  | Group value and category documentation | `data/external/psid_group_attribute_codebook_values_v1.json`, `data/external/group_category_schemes_v1.json`, and every `sources[*].committed_file` that `load_schemes` verifies (`data/group_attributes_psid.py:1324–1358`, `cohorts/group_attributes.py:90–97,186–215`). Pin these paths and versions separately from staged files. They were not opened here. |

  **Report cutoffs [frozen shipped behavior].** The group loader reads
  every listed report wave. Race/origin resolution uses 1985–2023;
  birthplace uses 2013–2023. Education resolution alone uses reports no
  later than `max(anchor_waves)` (2011 for the inherited cohort), although
  later education inputs are still read. The builder records these
  independent windows at `cohorts/group_attributes.py:992–1053`.
  The cohort loader's default birth-inference cutoff is 2023; an explicit
  cap affects family earnings/birth inference, not marriage history,
  Social Security report waves or the group loader.

  **Earnings reference years [separate].** The inherited career uses
  reference years through the 2010 opening year; the 2009-anchor
  alternative uses its 2008 opening year (`psid2010.py:1975–1984`). These
  career cutoffs do not reduce either shipped loader's input inventory.
  A prospective replacement needs a new complete dated file ledger and
  explicit birth-inference, marriage/report, group-report and availability
  filters; selecting earlier earnings years alone is insufficient.
  Pin the four permitted TR 2026 `DeathProbsE` sources and SM2's
  coefficient, reference-population and path tables as well.
  `cohorts/psid2010.record_files_read:930–966` audits staged file opens.
  No staged-data digest is claimed pinned by S0.1.
- **Power [frozen conditional grid].** The balanced approximation needs
  1,662 / 1,564 / 1,564 effective deaths per primary cell for earnings /
  education / race, with Bonferroni families 20 / 16 / 16. The first
  passing assumed person grid is 10,000 per cell at .25 death risk and
  design effect 1; all rate/design-effect alternatives are in section 6
  and the JSON. Successful rows do not establish feasibility for the
  PSID cohort. Actual structural precision and any rescoping remain open.
- **Analysis class [frozen finding; proposed registration label].** The
  shipped all-wave race resolution and 2011 cohort cannot establish a
  pre-2011 origin. Existing-input SM3 must be retrospective conditional.
  A new boundary-filtered, dated-release construction and unused outcome
  partition are prerequisites to any prospective claim; later external
  calibration does not supply them. No real-data step was performed or
  authorized by this audit. Max and the coordinator decide Q7.
