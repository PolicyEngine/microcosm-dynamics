# Track B B0.1: source, exposure, access and power audit for B2

**Status: audit record for B2, not yet reviewed.** The structural-audit
protocol at the end of this file was committed and pushed at `e51216f`
before any count ran. The count script then ran once, from a clean
worktree at that commit, and wrote `docs/design/track_b_b0_1_counts.json`.
Every number below comes from that file unless another source is cited.

Verification class: **source audit** (design §3.2, line 144). It admits
nothing scientific. Before B2 registers, the design requires two more
things:

- a blinded review of prospective feasibility and power (design §3.1
  row B0, line 120);
- a B1 replay that clears B2's dependency (line 121). Whether a B1 v2
  "reconstructed reproduction" pass suffices is Max's pending decision
  d622 (`docs/design/track_b_b1_v2_amendment.md:75-79`).

This record also leaves seven questions for Max (section 12).

"The design" means `microcosm-launch-evidence/dynasim-parity-20260909/trackb-design-20260928.md`
(revision 3), which sits outside this repository. Max approved its §10
defaults in d515 on 2026-09-28. Design line numbers refer to that file.

## 1. Summary

- **Sources.** B2 reads the PSID family files and the cross-year
  individual file already staged for M6. Every variable resolves under
  the repository's label checks (section 4). The pinned 2010 NAWI prefix
  in policyengine-us 1.752.2 matches the repository pin byte for byte.
- **Exposure.** Reference years 2012 and 2014 offer no unused
  holdout. Two public selection ledgers ran the forward law from a 2010
  pseudo-boundary and scored B2's own six M6-retained cells against
  realized 2012 and 2014 earnings. One ledger includes candidate 3's
  exact law (q = 0.55, ρ = −0.60). A third public artifact compared two
  of those cells draw by draw. The ledgers also publish the
  2010-boundary floor that B2 would derive for the six cells, and five
  floor seeds for all 21 earnings cells (section 5).
- **Population.** The domain is 13,542 heads and spouses with a valid
  2010 row, drawn from 23,134 persons present with positive weight at
  the 2011 wave. B2 scores 10,165 rows at 2012 and 9,310 at 2014.
  These counts equal the committed selector ledgers' counts exactly
  (section 7).
- **Power.** Under M6's own operating characteristic, a surface of 6
  uncapped floor-derived cells has p_gate = 0.974 and one of 16 has
  0.859, so the full battery cannot clear 0.90 without pruning. The design's §5.2 bound
  rule and §5.4's M6 discipline conflict at M6's k = 3 tolerance: on
  M6's side-A scoring basis a faithful cell passes the bound rule with
  probability 0.48 alone and 0 in a family of 6 (section 11).
- **§5.3 limits.** If applied to B2, lag-2 persistence at 0.05 is
  infeasible on B2's support at every family size. Participation at 3
  percentage points is feasible on Kish sizes for up to 6 cells but not
  under the worst-case household bound (section 11).
- **Seven open questions** need Max's ruling (section 12).

## 2. The §5.2 elements and where this record freezes them

Design §5.2 (lines 282-288) lists, for every empirical gate: source
release, variables, population, exposure history, holdout partition,
critical cells, numerical tolerances, uncertainty treatment and pass
conjunction. Its second paragraph (line 286) adds reference dates kept
separate from interview and publication availability, and it requires a
named power procedure. This audit reads that as ten elements plus the
power procedure.

| Element | Section | Status |
|---|---|---|
| 1. Source release | 4 | Frozen |
| 2. Variables | 4 | Frozen |
| 3. Population | 7 | Frozen |
| 4. Exposure history | 5 | Recorded; its consequence needs Q1 |
| 5. Holdout partition | 8 | Frozen; no unused partition exists |
| 6. Critical cells | 9 | Candidate family frozen; surface needs Q1 |
| 7. Numerical tolerances | 9 | Floor-derivation rule frozen; §5.3 use needs Q4 |
| 8. Uncertainty treatment | 10 | Needs Q2 and Q3 |
| 9. Pass conjunction | 10 | Inherited M6 conjunction recorded; needs Q2 |
| 10. Reference dates vs availability | 4.3 | Frozen |
| Named power procedure | 11 | Named; planning values need Q5 |

## 3. What B2 is

B2 builds `EarningsSpec(origin_year, estimation_cutoff, end_year,
age_support, wage_vintage)` and a 2010→2014 bridge, scored by a new
registered transport gate on 2012 and 2014 (design line 121). Its
verification class is retrospective regression, with admitted scope
"2010→2014 continuity on the stated surface, ages 25–64. Not a
2010-vintage forecast" (design line 150). Under this audit's reading of
the code, B2's spec values are:

| Field | Value | Source |
|---|---|---|
| `origin_year` | 2010 | design line 121 |
| `estimation_cutoff` | 2010: earnings rows with income-reference year ≤ 2010 | `forward_earnings.py:1021-1024` |
| `end_year` | 2014 | design line 121 |
| `age_support` | 25-64 for estimation and scoring | `forward_earnings.py:66-67`, `:1030-1032` |
| `wage_vintage` | policyengine-us 1.752.2 `nawi.yaml`, realized through 2010; later years from a log-linear fit over 2001-2010 | `forward_earnings.py:435-460`, `:1038-1049` |

The fitter already takes `boundary_year` as a parameter
(`forward_earnings.py:1004-1012`). The committed `EARNINGS_SPEC` still
names its wage projection `ols_log_nawi_2005_2014`
(`src/populace_dynamics/engine/refit.py:77-102`), so B2's spec must carry
its own vintage label rather than reuse that record.

The law B2 transports is candidate 3's (q = 0.55, ρ = −0.6; design line
31). Its structure is in-sample for selection
(`gates.yaml:5445-5456`). B2 inherits the §2 disclosure of candidate 3
in full (design lines 29-41).

## 4. Sources and variables (elements 1, 2 and 10)

### 4.1 Files and hashes

The repository does not pin raw PSID file hashes for M6: the B1 draft
records that the candidate-3 artifact "does not provide an archived
raw-PSID hash manifest" (`docs/design/track_b_b1_registration_draft.md:164`).
This audit therefore records them. `track_b_b0_1_counts.json` holds:

- `psid_files_opened_sha256`: the eight files the count run opened,
  recorded through the repository's own audit hook
  (`src/populace_dynamics/cohorts/psid2010.py:930-965`);
- `b2_read_set_sha256`: 80 files, the `.txt` and `.sps` of every family
  wave from 1968 through 2015 plus `IND2023ER.txt` and `IND2023ER.sps`.
  This is the set a B2 fit (waves through 2011) and B2 truth (2013, 2015)
  would read.

The eight files B2's target years depend on:

| File | SHA-256 |
|---|---|
| `family/2011/FAM2011ER.txt` | `3253586567a76a43d3e4a568dd5ca8af0f8a3c69db829d6a55bdf0942c60992f` |
| `family/2011/FAM2011ER.sps` | `6a994d8b65803a515eaa3bf62c74e278dd5943b8b578428ef4fd462d96cba45c` |
| `family/2013/FAM2013ER.txt` | `0406aed042d660f51712d0f18a6e80f939717c0c2fc68b8d3a8d6dcbf48180e1` |
| `family/2013/FAM2013ER.sps` | `526595b50a2087adc635da3c1288a396aa7179b075c11506f10338ab6348a0b5` |
| `family/2015/FAM2015ER.txt` | `e4a64b275a9c6dbe8e7b562be7ed0906d4082b0c49cad79d764c69b8de318ec2` |
| `family/2015/FAM2015ER.sps` | `6500c8e88a2353e7a6c5322a898f3879662228fdefa329e0901eb254fc9e3fff` |
| `ind2023er/IND2023ER.txt` | `d68554ac828a690491572f37323eba1d8488e8b0001ed2aa89df4d4ade26c869` |
| `ind2023er/IND2023ER.sps` | `92d32d0efd65d50e984e971c681f6e9231b720973444cdc8f20f397039c9a462` |

The wage index is the policyengine-us 1.752.2 `nawi.yaml`, read through
the q\* selector's prefix reader, which stops at the 2010 key
(`scripts/select_m6_qstar_train_only.py:513-585`). The check read 1,588
bytes with prefix SHA-256 `e272a7bc…40d7` and mapping SHA-256
`26b6a049…582c`. Both equal the repository pin
(`select_m6_qstar_train_only.py:184-192`), and all ten fit-decade keys,
2001-2010, are present.

### 4.2 Variables and labels

Every variable resolved through the repository's label patterns
(`src/populace_dynamics/data/panels.py:58-72`;
`src/populace_dynamics/data/family.py:596-597`, `:703-775`). Labels
below are whitespace-normalized.

| Concept | 2011 wave | 2013 wave | 2015 wave |
|---|---|---|---|
| Age | `ER34104` AGE OF INDIVIDUAL 11 | `ER34204` AGE OF INDIVIDUAL 13 | `ER34305` AGE OF INDIVIDUAL 15 |
| Sequence | `ER34102` | `ER34202` | `ER34302` |
| Relationship | `ER34103` RELATION TO HEAD 11 | `ER34203` | `ER34303` |
| Weight | `ER34155` CORE/IMM INDIVIDUAL CROSS-SECTION WT 11 | `ER34269` (… WT 13) | `ER34414` (… WT 15) |
| Individual interview | `ER34101` | `ER34201` | `ER34301` |
| Family interview | `ER47302` | `ER53002` | `ER60002` |
| Head labor income | `ER52237` LABOR INCOME OF HEAD-2010 | `ER58038` …HEAD-2012 | `ER65216` …HEAD-2014 |
| Spouse labor income | `ER52249` LABOR INCOME OF WIFE-2010 | `ER58050` …WIFE-2012 | `ER65244` LABOR INCOME OF SPOUSE-2014 |
| Head accuracy | `ER52220`, `ER52236` (wages; misc labor) | `ER58021`, `ER58037` | `ER65201`, `ER65215` |
| Spouse accuracy | `ER52250` (single total flag) | `ER58051` | `ER65229`, `ER65243` (wages; misc labor) |

Each labor-income label carries its reference year, which the loader
checks against wave − 1 (`family.py:675-683`). Two label changes fall
inside B2's window, both at the 2015 wave:

- the spouse income label changes from WIFE to SPOUSE;
- the spouse accuracy flag splits into wage and miscellaneous parts
  (`family.py:301-305`, `:539-548`).

The loader treats both years' spouse income as one concept. This audit
checked labels only. It did not check the codebooks for a change of
concept. No pre-1994 concept seam lies inside B2's window
(`family.py:25-32`).

### 4.3 Reference dates, collection and availability (element 10)

| Quantity | Reference period | Collected at | Staged release |
|---|---|---|---|
| Anchor earnings | 2010 | 2011 interview | `FAM2011ER`, Release 6, June 2023 (readme p. 1) |
| Horizon earnings | 2012 | 2013 interview | `FAM2013ER`, release notes through Release 4, June 2023 |
| Horizon earnings | 2014 | 2015 interview | `FAM2015ER`, Release 2, June 2023 |
| Age, sequence, relationship, weight | 2011, 2013 and 2015 waves | same | `IND2023ER`, Release 2, December 2025 |
| Wage index | NAWI 2001-2010 | not applicable | policyengine-us 1.752.2 |

PSID has no 2012 or 2014 interview: interviews are biennial on odd years
from 1999 (`family.py:52-55`). "B2's 2012/2014 waves" therefore means
income-reference years 2012 and 2014, collected in 2013 and 2015
(`family.py:843`). Age and weight are measured at the collection wave
(`family.py:799-800`).

All staged files are retrospective releases, made 9 to 13 years after
their reference years. The selectors record the same fact
(`select_m6_qstar_train_only.py:645`). This audit did not verify any
wave's first public release date, or when SSA first published NAWI for
2010. B2 is therefore not a real-time or 2010-vintage exercise; §3.2
already says so (design line 150).

## 5. Exposure history (element 4)

### 5.1 Uses of reference years 2012 and 2014 that bear on B2

1. **Structural selection of the forward law.** gate_1's primary
   earnings views use the family panel over reference years 1998-2022
   (`gates.yaml:50-68`). The M6 forward law mirrors that full-window
   selected specification, so its structure is in-sample for selection
   (`gates.yaml:5445-5456`).
2. **Candidate 3's fit.** Candidate 3 was fitted on reference years
   through 2014 (`scripts/registered_m6_candidate2_inputs.py:9-14`,
   `:77-79`; `forward_earnings.py:1021-1032`). 2014 is its anchor year
   (`forward_earnings.py:1055-1062`) and 2012 its start lag (`:1111-1117`).
3. **M6 truth.** M6's change cells pair 2014 with 2016
   (`src/populace_dynamics/harness/m6_cells.py:37`, `:481`), so 2014
   levels entered M6's scored truth.
4. **Train-only selection at pseudo-boundary 2010, on B2's own
   estimand.** The q\* and ρ\* selectors refit the complete forward law
   on rows dated ≤ 2010. They projected 2010 → 2012 → 2014 and scored
   six cells against realized 2012 and 2014 earnings on the support B2
   would use (`docs/design/m6_projection_engine.md:1076-1140`;
   `select_m6_qstar_train_only.py:1410-1565`). The six cells are
   `earn_p10.prime`, `earn_dlog_mean.prime`, `earn_dlog_sd.older`,
   `earn_mob_h1_diag`, `earn_autocorr_lag2` and `earn_zero_rate.older`.
   The objective J(q) summed standardized squared scores over boundaries
   2006, 2008 and 2010 (`m6_projection_engine.md:1133-1140`). q = 0.55
   was selected on it (`docs/design/m6_candidate3_program.md:202-228`).
5. **F1 mechanism diagnostic.** At boundary 2010 with q = 0.55, it
   compared projected and realized 2012 and 2014 mean Δlog earnings
   (prime) and lag-2 autocorrelation, draw by draw. It carries the caveat
   that "the evaluated waves sat inside q\*'s selection evidence"
   (`m6_candidate3_program.md:237-253`).
6. **The paper.** Figure `fig-m6-frontier` plots q\* objective
   contributions summed over the three pseudo-boundaries, 2010 included
   (`paper/paper.qmd:2246`; `scripts/build_paper_figures.py:571-625`).
7. **Marital selectors at pseudo-boundary 2010.** The first-marriage
   and remarriage selectors also used boundaries 2006, 2008 and 2010
   (for example `docs/analysis/m6_first_marriage_c_selection.md`). They
   bear on B4, not on B2's earnings surface, and are recorded here for
   B0.2.

### 5.2 What the committed artifacts contain for boundary 2010

This audit read the artifacts' key names, metadata strings and count
fields. It read no value field.

| Artifact | SHA-256 | Merged | 2010-boundary content (by field name) |
|---|---|---|---|
| `docs/analysis/m6_qstar_train_only_selection_results.json` | `d25b8e15…25bb` | #255, 2026-07-18 | 100-seed floor (mean, SD, realized σ, events) and full-support truth moments for the six cells; half-split scores and event counts at floor seeds 0-4 for all 21 earnings cells; aggregate projected moments and objective contributions for 21 q rungs |
| `docs/analysis/m6_rhostar_train_only_selection_results.json` | `db7fe835…63ff` | #273, 2026-07-23 | Same floor, truth and seed-detail fields; aggregates for 17 ρ rungs at fixed q = 0.55, including ρ = −0.60, candidate 3's law |
| `docs/analysis/m6_c3_f1_mechanism_diagnostic_results.json` | `dcd1bf35…a0bb` | #271, 2026-07-22 | Per-draw projected and realized mean Δlog (prime) and lag-2 autocorrelation at q = 0.55 |

The 21 cells in the seed detail are the 16 gateable cells plus 5
report-only cells (section 9). The q\* reducer states that it removed the
per-draw projected records
(`m6_qstar_train_only_selection_results.json`, field `reducer.removed`).
This audit did not check which cells the removed records covered.
Across all tracked files, only these three artifacts hold 2010-boundary
earnings content; the other matches are the marital selectors.

The repository is public, so all three have been public since they
merged.

### 5.3 Who has seen them

- **The lanes that produced them.** PRs #255, #271 and #273 were merged
  under Max Ghenis's GitHub account.
- **Anyone reading the public repository or paper figure 5.**
- **The Track B design's authors.** They state that 2012/2014 were
  selection evidence (design lines 121, 150, 333). Their current-run
  inventory (design lines 507-553) lists none of these artifacts, so this
  audit has no evidence that they read the values.
- **This audit's author.** See section 14.

### 5.4 Consequences for B2

- **No unused partition exists on B2's target years.** Design line 286:
  "Previously inspected outcomes remain regression evidence". §3.2
  already classes B2 as retrospective regression (design line 150).
- **The six cells' floor already exists.** Under the default
  translation in section 9, B2's floor for the six M6-retained cells is
  by construction the floor the selectors published. The constructions
  match: same anchor, domain, split order, seeds, reducer, years and
  fixed weights (`select_m6_qstar_train_only.py:1416-1479`). The
  selectors published candidate-3-law outcomes on the same cells in the
  same record.
- **What the ordering rule can still bind.** "Floors derived before
  candidate outcomes" (design line 332) can bind B2's own registered run,
  but not what is already public (Q1).

## 6. Access

- **Staged data.** PSID files live at `~/PolicyEngine/psid-data`,
  resolved on this machine to `/Users/maxghenis/PolicyEngine/psid-data`.
  The staging README records the download under Max's registered PSID
  account on 2026-07-03 (`psid-data/README.md:3-4`). It records family
  downloads as login-gated (`README.md:42`). Its family-file section
  still reads "enumerated, not yet fetched" (`README.md:34`), but
  `family/` holds a directory for every wave from 1968 to 2023, and
  every file in B2's read set was present and hashed.
- **Not in the repository.** No PSID data file is tracked. The only
  path match is a questionnaire PDF,
  `tests/data/track_u2/psid_docs/fam2015_QxQs.pdf`. CI cannot run B2's
  real-data steps, and PSID-dependent tests skip off-machine
  (`CLAUDE.md:117`).
- **Wage index.** The public policyengine-us 1.752.2 package. The check
  used a local install at
  `_buildg-runtime/venvs/venv-1752/.../policyengine_us/parameters/gov/ssa/nawi.yaml`.
- **Fitting stack.** Fitting needs the populace-fit stack in a
  dedicated environment (`CLAUDE.md:17`). B1's draft pins candidate 3's
  runtime (`track_b_b1_registration_draft.md:121-125`). B0.1 did not
  install or verify that runtime.
- **Restricted files.** No B2 source appears in the evidence
  directory's `RESTRICTED-FILES.md`, and B2 reads no DYNASIM comparator.
  Two restricted scratchpad archives there hold PSID codebook text and
  working files traced on real data (`RESTRICTED-FILES.md:57-58`). B2
  builders must not source from them.

## 7. Population and support (element 3)

### 7.1 Anchor and domain

| Quantity | Count | Ledger (both selectors) |
|---|---:|---:|
| Full anchor: sequence 1-20, positive weight, 2011 wave | 23,134 persons in 8,907 families | 23,134 |
| Domain: full-anchor persons with a valid 2010 row | 13,542 | 13,542 |
| Domain heads / spouses or partners | 8,907 / 4,635 | not recorded |
| Domain age at 2011: under 25 / 25-44 / 45-64 / 65+ | 950 / 6,092 / 4,974 / 1,526 | not recorded |

The domain holds 8,907 heads. The 2011 anchor spans 8,907 families,
which is the record count of `FAM2011ER` (readme p. 1). The estimation
panel is restricted to ages 25-64 (`forward_earnings.py:1030-1032`), but anchors
are not: anchors come from every positive-weight 2010 row
(`:1055-1057`). An anchor with no estimation row gets u_w = 0.5
(`:1063-1066`), and projection clips out-of-range ages into the edge
bins (`:218-222`). So the 950 domain persons under 25 and the 1,526 aged
65+ are projected. Scoring counts them only while their collection-wave
age is 25-64.

### 7.2 Scored support

| Reference year (wave) | Scored rows | Prime 25-44 | Older 45-64 | Valid domain rows outside 25-64 | Assigned or edited |
|---|---:|---:|---:|---:|---:|
| 2010 (2011) | 11,066 | 6,092 | 4,974 | 2,476 | 584 (5.3%) |
| 2012 (2013) | 10,165 | 5,511 | 4,654 | 2,061 | 461 (4.5%) |
| 2014 (2015) | 9,310 | 4,909 | 4,401 | 1,863 | 450 (4.8%) |

Scored rows by year match the ledgers' `truth_support_rows_by_period`
exactly (11,066, 10,165, 9,310), as does the 2012 + 2014 endpoint total
of 19,475. The two independent implementations therefore agree on
anchor, domain and support. "Assigned or edited" counts scored rows with
a positive PSID accuracy code. It is a data-quality count, not an
earnings value.

**Age convention.** Cohort and support use age at the collection wave
(`family.py:799-800`, `:852`; `select_m6_qstar_train_only.py:1451`), not
age in the reference year. The comment at `m6_cells.py:89` calls the
cohort "age at reference year". B2's registration must state
collection-wave age.

### 7.3 Exits from the domain

| Disposition | 2012 | 2014 |
|---|---:|---:|
| Scored | 10,165 | 9,310 |
| Valid row, age outside 25-64 | 2,061 | 1,863 |
| Present, other relationship | 31 | 77 |
| Institution (sequence 51-59) | 23 | 17 |
| Moved out (71-80) | 341 | 245 |
| Died (81-89) | 79 | 93 |
| Not in a responding family (any other sequence value, including 0) | 842 | 1,937 |
| Head or spouse with earnings at the missing sentinel | 0 | 0 |
| Present with non-positive weight | 0 | 0 |
| Present with no family record | 0 | 0 |
| **Total (= domain)** | **13,542** | **13,542** |

Sequence 81-89 marks a death between the previous and the current
interview, and 71-80 a move-out (`docs/design/psid2010-cohort.md:24-27`).
The 2014 "not in a responding family" row can therefore include persons
who died or moved out before the 2013 interview, as well as
nonresponse. This audit did not separate them.

No head or spouse row sat at the missing sentinel. That is consistent
with the loader's note that family labor income is edited
(`family.py:617-618`).

### 7.4 Entrants B2 does not score

Persons with a valid row aged 25-64 at a horizon year who are outside
the domain:

| Horizon | In the 2011 anchor without a valid 2010 row (prime / older) | Outside the 2011 anchor (prime / older) | Total |
|---|---|---|---:|
| 2012 | 239 / 40 | 553 / 150 | 982 |
| 2014 | 450 / 59 | 963 / 200 | 1,672 |

B2's closed-domain scoring excludes them, as M6's closed-domain floor
excluded later entrants (`docs/amendments/gate_m6_amendment_1_closed_domain_floors.md:45-56`).
B2 therefore admits nothing about entrants (design §3.4, lines 218-220).

### 7.5 Weights and effective sizes

The fixed weight is each person's 2011 cross-section weight, `ER34155`
(`select_m6_qstar_train_only.py:1443`). This is the B2 analog of M6's F6
start-wave weight (`gates.yaml:5519-5524`). The household identifier is
the 2011 interview number.

| Row set | Rows | Persons | Households | Kish n_eff | Household-worst n_eff |
|---|---:|---:|---:|---:|---:|
| Level cells, prime (2012 + 2014) | 10,420 | 5,911 | 4,236 | 6,122 | 2,303 |
| Level cells, older | 9,055 | 5,159 | 3,592 | 5,952 | 2,100 |
| Level cells, pooled | 19,475 | 10,668 | 7,255 | 11,893 | 4,022 |
| Change pairs, prime (two-year steps) | 9,558 | 5,472 | 3,928 | 5,653 | 2,133 |
| Change pairs, older | 8,148 | 4,603 | 3,224 | 5,362 | 1,886 |
| Change pairs, pooled two-year | 18,510 | 10,126 | 6,887 | 11,369 | 3,825 |
| Pairs, pooled four-year (2010-2014) | 8,639 | 8,639 | 6,007 | 5,310 | 3,448 |
| Domain persons | 13,542 | 13,542 | 8,907 | 8,355 | 5,248 |

The household-worst size assumes every row in a 2011 household is
perfectly correlated, including a person's two years and a couple's
rows. The true effective size lies between the two columns for any
non-negative within-household correlation. Pinning it down needs
outcome data (Q5).

These counts include every valid row. Cells on log earnings (quantiles,
Δlog moments, mobility, autocorrelation) use only positive earners, so
the counts above are upper bounds for those cells.

## 8. Holdout partition (element 5)

- **Estimation.** Earnings rows with reference year ≤ 2010
  (`forward_earnings.py:1021-1024`), fitted at ages 25-64. NAWI is
  realized through 2010 and projected after it.
- **Evaluation.** Realized 2012 and 2014 rows on the 2010 domain,
  collection-wave ages 25-64.
- **Inherited M6 structure.** Gate seeds 0-4 each choose a 50% person
  split "side A" and score it (`src/populace_dynamics/harness/m6_scoring.py:394-425`,
  `:624-733`). Floor seeds 0-99 split the full anchor into halves
  (`m6_cells.py:614-689`).
- **No unused partition.** Every evaluation row lies in the years
  section 5 lists as exposed. "'Later' or 'external' does not establish
  an unused holdout" (design line 286).

## 9. Cells and floor-derivation rule (elements 6 and 7)

### 9.1 The candidate cell family

With `level_years = (2012, 2014)` and `change_years = (2010, 2012,
2014)`, the M6 reducer `earnings_cells` (`m6_cells.py:477-587`) yields
21 cells:

| Cells | Metric | Cap | M6 v3 retained |
|---|---|---|---|
| `earn_p10`, `earn_p50`, `earn_p90` × prime, older | log ratio | ln 1.5 | `p10.prime` |
| `earn_zero_rate` × prime, older | log ratio | ln 1.5 | `zero_rate.older` |
| `earn_dlog_sd` × prime, older | log ratio | ln 1.5 | `dlog_sd.older` |
| `earn_dlog_mean` × prime, older | absolute gap (log units) | ln 1.5 | `dlog_mean.prime` |
| `earn_mob_h1_diag`, `earn_mob_h2_diag` | log ratio | ln 1.5 | `mob_h1_diag` |
| `earn_autocorr_lag1`, `earn_autocorr_lag2` | absolute gap (correlation) | 0.15 | `autocorr_lag2` |
| `earn_dlog_skew`, `earn_dlog_kurt` × prime, older | report-only shape | none | no |
| `earn_autocorr_lag5` | report-only horizon | none | no |

The first six rows are the 16 gateable cells (metrics and caps:
`m6_cells.py:593-612`, `:746-752`; retained set:
`gates.yaml:5600-5610`). On B2's three-year window a 10-year
autocorrelation is undefined, as in M6 (`m6_cells.py:564-586`).

Which of these cells B2 gates is open (Q1). The six M6-retained cells
are the most exposed (section 5.2). The other ten have published
five-seed floor detail at boundary 2010 but no published candidate
outcome.

### 9.2 Floor-derivation rule, to run before any B2 candidate outcome

This carries forward M6's discipline (design lines 330-333) with B2's
years. It uses no 2016/2018 tolerance.

1. B2's registration on #42 pins the floor builder's commit and this
   rule before the builder runs.
2. The builder is truth-only. It defines the domain from data alone:
   2011 anchor persons with a valid 2010 row. The selectors assert that
   this set equals the fitted anchor set
   (`select_m6_qstar_train_only.py:1430-1441`), and this audit's
   data-only definition reproduces the ledgers' domain count of 13,542.
   The builder therefore needs no fit or projection object. It
   records that it read no candidate or projection artifact, as M6 v4's
   builder did (`gate_m6_amendment_1_closed_domain_floors.md:40-43`, `:132`).
3. For each floor seed 0-99, it splits the full 2011 anchor 50/50 by the
   registered split unit, then intersects each half with the domain.
   This is M6's F7 order (`gate_m6_amendment_1_closed_domain_floors.md:58-60`;
   `select_m6_qstar_train_only.py:1470-1479`). The split unit is open
   (Q3).
4. For each cell, it scores |ln(a/b)| or |a − b| between the halves by
   the cell's metric (`m6_cells.py:593-612`). It then records the mean,
   sample SD, realized σ = √(mean² + SD²), defined-seed count and
   weakest-half event count (`m6_cells.py:614-689`).
5. A cell can gate only if all 100 seeds are defined and the weaker half
   holds at least 20 events on every seed (`m6_cells.py:56`).
6. Tolerance = round(mean + 3 × SD, 3), capped at the metric cap
   (`m6_cells.py:48`, `:691-698`, `:746-752`). Whether §5.3's limits
   also cap B2 is open (Q4).
7. The surface is selected by the ruled rule (Q1). The builder computes
   the operating characteristic of section 11 and requires p_gate ≥ 0.90
   (`m6_cells.py:64`). It also applies the vacuity guards: not every
   tolerance at its cap, and at least `MIN_GATED_CELLS_FOR_POWER`
   cells where the ruling keeps that guard (`m6_cells.py:67`).
8. The builder publishes the floor artifact and its hash. B2's candidate
   runs only after the floor is committed.

Under this rule, the six-cell floor must equal the published selector
floor, and the five-seed detail must equal the published seed detail. A
B2 build can test that differentially. That equality is also why the
six-cell floor is not new information (section 5.4).

## 10. Uncertainty treatment and pass conjunction (elements 8 and 9)

**Inherited M6 rule** (design §5.4, lines 330-333):

- for each gate seed, score the mean of K = 20 draws on side A against
  side-A truth;
- a seed passes when every gated cell is within tolerance and no draw is
  undefined or unregenerated;
- the gate passes on at least 4 of 5 seeds (`m6_scoring.py:35-38`,
  `:624-752`).

Uncertainty enters only through the half-split floor and the 4-of-5
conjunction.

**§5.2 rule** (design lines 299-304):

- each critical cell's simultaneous 95% bound, Bonferroni over the
  registered family, must lie within its tolerance;
- resampling respects survey design and family clusters;
- Monte Carlo error must be below a tenth of the tolerance;
- insufficient precision is inconclusive.

The two rules conflict in two ways, quantified in section 11:

- **The pass rule.** At the k = 3 floor tolerance, a faithful candidate
  almost never passes the bound rule on M6's side-A basis (Q2).
- **The split unit.** M6 splits earnings by person
  (`gates.yaml:5533-5537`), which places spouses in different halves.
  §5.2 asks resampling to respect family clusters. In B2's domain, 4,635
  of 13,542 persons share a 2011 household with a domain head (Q3).

## 11. Prospective power and feasibility

**Named procedure.** The operating characteristic is P(gate pass |
faithful candidate) on M6's independence-approximation half-normal
basis. A faithful cell's score is half-normal with the floor's realized
σ; cell pass = 2Φ(tolerance/σ) − 1; seed pass is the product over gated
cells; gate pass = P(at least 4 of 5 seeds)
(`m6_cells.py:701-734`). It is evaluated on B2's own floor artifact
before the candidate run. For the §5.2 rule the characteristic is
P(|gap| + z\* se ≤ tolerance | faithful), with se covering survey,
simulation and estimation error.

Everything below uses only sample sizes, weights and the rules' algebra.
It uses no B2 outcome.

### 11.1 M6 rule: structural limits

For a half-normal score, the k = 3 floor tolerance is 2.6063 σ, so a
faithful cell passes with probability 0.99085. The tolerance does not
depend on σ until it reaches the cap.

| Gated cells | p_gate (4 of 5) |
|---:|---:|
| 1 | 0.9992 |
| 6 | 0.9742 |
| 16 | 0.8590 |

At most 12 uncapped cells keep p_gate ≥ 0.90 on this basis, so the full
16-cell battery cannot clear the weak-power floor without pruning.

M6 v4's published 2016/2018 floor gives the realized tolerance/σ ratios
M6 actually achieved: 2.35-2.64
(`gate_m6_amendment_1_closed_domain_floors.md:70-75`; not B2 data).
Those ratios allow 6 to 14 cells. The same arithmetic reproduces v4's
published six-cell p_gate of 0.9575, which independently checks this
script's `p_gate` against M6's record.

Monte Carlo error: with tolerance 5.21 × se on full support or
3.69 × se on half support, se/√K falls below a tenth of the tolerance
from K = 4 or K = 8. K = 20 meets both.

### 11.2 §5.2 bound rule

Tolerance/se needed for 0.90 power:

| Family size m | z\* (Bonferroni 95%) | Needed tol/se | Pass probability at the k = 3 floor tolerance, side-A basis | k a floor tolerance would need |
|---:|---:|---:|---:|---:|
| 1 | 1.960 | 3.605 | 0.482 | 4.66 |
| 6 | 2.638 | 4.283 | 0.000 | 5.78 |
| 16 | 2.955 | 4.600 | 0.000 | 6.31 |

On M6's own basis, where a faithful candidate's gap has the half-split
σ, the k = 3 tolerance of 2.61 σ leaves a margin of 2.61 − z\* over the
Bonferroni critical value. The pass probability falls from 0.48 at
m = 1 to 0.28, 0.17, 0.09 and 0.02 at m = 2 to 5. From m = 6, z\*
exceeds 2.61, so the bound rule cannot pass at all. These intermediate
values come from the same functions and are outcome-free.

The following figures were derived after the run from the frozen record
by outcome-free arithmetic; they are not part of the frozen record.
With full-support scoring instead of side A, the gap se is at least
se_full × √(1 + 1/K), so the k = 3 tolerance is 5.09 of those units.
The bound rule then passes with probability 0.998, 0.986 and 0.967 for
m = 1, 6 and 16. That holds only if estimation uncertainty adds no more
than 104%, 43% and 23% of that variance. This audit did not bound the
estimation term (Q2).

### 11.3 §5.3 earnings limits evaluated on B2's support

§5.3's earnings row (design line 312) was written for B3's bands at
ages 62-69. Whether it applies to B2 is open (Q4). This section shows
what it would demand. Each figure uses the bound rule with K = 20 and
no estimation term, so each is a necessary condition only.

**Participation, 3 percentage points, worst case p = 1/2.** Required
n_eff is 3,790 for m = 1, 5,351 for m = 6 and 6,172 for m = 16.

| Cohort | Kish n_eff | Household-worst n_eff | Feasible at m = 1 / 6 / 16 (Kish) | Feasible (household-worst) |
|---|---:|---:|---|---|
| Prime | 6,122 | 2,303 | yes / yes / no | no at any m |
| Older | 5,952 | 2,100 | yes / yes / no | no at any m |

**Positive-earnings quantiles, 10% (tolerance ln 1.1).** Under a
log-normal planning model with every row positive, the largest
log-earnings SD a cell tolerates at m = 6 is:

| Cohort | p10 or p90, Kish / worst | p50, Kish / worst |
|---|---|---|
| Prime | 0.99 / 0.61 | 1.36 / 0.83 |
| Older | 0.98 / 0.58 | 1.34 / 0.79 |

With positive share π, each limit scales by √π. Other family sizes are
in the counts file. Feasibility turns on a dispersion planning value
this audit may not compute from 2012 or 2014 (Q5).

**Persistence correlation, 0.05.** Using the delta-method bound
se(r) ≤ 1/√n, the required effective positive pairs are 5,458, 7,705
and 8,887 for m = 1, 6 and 16.

| Pairs | Kish n_eff | Household-worst n_eff | Minimum positive share, m = 1 / 6 / 16 (Kish) | Household-worst |
|---|---:|---:|---|---|
| Lag 1 (two-year steps, pooled) | 11,369 | 3,825 | 0.48 / 0.68 / 0.78 | above 1 at every m |
| Lag 2 (2010-2014) | 5,310 | 3,448 | 1.03 / 1.45 / 1.67 | above 1 at every m |

Lag-2 persistence at 0.05 cannot be met on B2's support at any family
size, even if every pair were positive, under either effective size.
Under the design's blocking rule (design line 445), that is a
`WEAK_POWER_OR_VACUITY` case needing prospective rescoping before any
candidate outcome (design line 454).

### 11.4 What this analysis does not settle

- **Estimation uncertainty.** It is not bounded here. The fit uses
  321,500 rows dated ≤ 2010: that is the selectors' `fit_input_rows`,
  a count read from the ledgers.
- **Planning values.** Positive-earner shares, log-earnings dispersion
  and the true household design effect need planning values (Q5).
- **The blinded review.** It has not run (Q6).

## 12. Open questions for Max

1. **Which cells does B2 gate, given the exposure in section 5?**
   - The six M6-retained cells already have a public 2010-boundary
     floor, public truth moments and public candidate-3-law outcomes.
   - The other ten gateable cells have public five-seed floor detail
     only.
   - Options:
     - (a) the six retained cells, knowing B2 largely re-scores a
       published computation with new draw seeds;
     - (b) the 16-cell battery, pruned by a candidate-blind rule on
       B2's own floor, such as M6's ladder (`gates.yaml:5590-5599`);
       on the half-normal basis at most 12 uncapped cells clear 0.90;
     - (c) another candidate-blind rule.
   - A related question: does "floors derived before candidate outcomes"
     bind only B2's own registered run?
2. **How do §5.2's bound rule and §5.4's M6 discipline combine?**
   - At M6's k = 3 tolerance on side-A scoring, a faithful cell passes
     the bound rule with probability 0.48 alone and 0 in a family of 6
     or 16.
   - Options:
     - the M6 rule alone;
     - the bound rule with full-support scoring and a registered bound
       on estimation uncertainty;
     - a floor tolerance with k near 5.8 (m = 6);
     - another composition.
3. **Should the floor and gate seeds split by person, as M6 does, or by
   2011 household, as §5.2's "respects family clusters" implies?** The
   worst-case household design effect cuts effective sizes by a factor
   of 1.5 to 3.0.
4. **Do §5.3's earnings limits apply to B2 at all?** They were written
   for B3's bands at ages 62-69. If they do apply:
   - lag-2 persistence at 0.05 is infeasible on B2's support;
   - lag-1 persistence needs a positive-pair share of at least 0.48 to
     0.78;
   - participation at 3 points fails under the household-worst bound.
5. **Which planning values may the B2 registration use for dispersion,
   positive shares and the household design effect?** Options:
   - B2's own ≤ 2010 training window;
   - M6's published 2016/2018 floor;
   - none, keeping this audit's sample-size bounds.
6. **Who performs the blinded review that design §3.1 requires for B0,
   and what may that reviewer not open?** This audit's author is not
   blind (section 14). A candidate exclusion list:
   - the three 2010-boundary artifacts in section 5.2;
   - `m6_candidate3_program.md:200-253`;
   - paper figure `fig-m6-frontier`;
   - the q\* and ρ\* analysis notes.
7. **Is a count of the population H will start from part of B2's
   registration, or does it move to B0.2 with H?** B2 scores only the
   closed 2010 domain at ages 25-64. 950 domain persons under 25 and
   1,526 aged 65+ at 2011 are projected but never scored at those ages.
   982 and 1,672 in-support rows outside the domain at 2012 and 2014
   are not scored at all.

d622, on B1 v2 unlocking B2, is already queued and is not repeated here.

## 13. Handoffs

- **To B0.2.**
  - Record B2's result as exposed before J's holdout is chosen (design
    lines 297, 368).
  - The marital selectors' pseudo-boundary 2010 bears on B4.
  - B3L's 2006 boundary coincides with a q\* and ρ\* pseudo-boundary
    whose floor and outcomes are also in the ledgers.
- **To B2.**
  - State collection-wave age and the reference-year versus
    collection-wave mapping (section 4.3).
  - Label the wage vintage separately from `ols_log_nawi_2005_2014`.
  - Reuse the 80-file hash set in `b2_read_set_sha256` as its source
    pin.
  - Carry the §2 candidate-3 disclosure in full.

## 14. Files read and this audit's exposure

This audit read `RESTRICTED-FILES.md` first and opened no restricted
file and no DYNASIM comparator value.

It read:

- design §§1-13;
- d515 and d622 in the decision log;
- `CLAUDE.md` and `CONTRIBUTING.md`;
- `engine/forward_earnings.py`, `engine/refit.py`,
  `engine/earnings_domain.py`, `forward_earnings_history.py` and
  `docs/design/forward-earnings-history.md`;
- `data/family.py`, `data/panels.py` and `data/psid.py`;
- `harness/m6_cells.py` and `harness/m6_scoring.py`;
- the `gate_m6` block of `gates.yaml` (lines 5324-5745) and its views
  (lines 13-117);
- the M6 input factories;
- the q\* selector's source-loading and boundary-context code;
- `docs/design/m6_projection_engine.md:1060-1140`;
- `docs/design/m6_candidate3_program.md:200-300`;
- `gate_m6_amendment_1_closed_domain_floors.md:1-140`;
- the B1 draft and amendment;
- `psid2010-cohort.md:1-80`;
- the staging README and PSID release readmes.

From the three 2010-boundary artifacts it read key names, metadata
strings, provenance, hashes and the count fields listed in the protocol.

**Exposure.** `m6_candidate3_program.md:218-228`, read for this audit,
states 2010-boundary objective contributions: the lag-2 autocorrelation
term at q = 0.55 and q = 1, and the mobility term at q = 1. They are
standardized squared scores of B2 cells on 2012 and 2014. This audit's
author is therefore not blind to part of B2's candidate outcomes. The
author also read M6 v4's 2016/2018 floor table, and a search printed one
row of that amendment's candidate-1 seed-score table
(`gate_m6_amendment_1_closed_domain_floors.md:143`). Neither is B2 data.
The count run computed no B2 cell, floor or candidate outcome; its
`outcome_blind` block and the unit test pinning its invariance to
earnings values record that.

## 15. Protocol record

The block below is byte-identical to the protocol committed at
`e51216f` before any count ran. Its SHA-256, over the text from the
begin marker through the end marker, is
`345c82ee74dcf89f2ae7021751d71ec17992e30d7aa4a1fff9060dd4fd707f89`;
the unit test `tests/test_track_b_b0_1_audit_record.py` pins it. Its line citations
into `scripts/track_b_b0_1_counts.py` refer to the script as frozen.

<!-- protocol:begin -->
## Structural-audit protocol (frozen before any count)

### What this audit may and may not compute

The Track B design (revision 3, `microcosm-launch-evidence/dynasim-parity-20260909/trackb-design-20260928.md`)
requires B2's floors to be "derived before candidate outcomes" (§3.1 row
B2, line 121; §5.4, lines 330-333). B0.1 therefore computes no B2 gate
statistic, candidate outcome, floor or cell value on reference years 2012
or 2014. It runs no projection and fits no model.

It may count records, verify variable labels and coverage, hash source
files, and derive design-based power quantities from sample sizes and
weights. It never counts zero, positive or imputed-to-zero earnings for
any reference year, because a zero share is a B2 cell (`earn_zero_rate`,
`src/populace_dynamics/harness/m6_cells.py:506-512`).

### Inputs

1. The staged PSID directory, resolved by the repository's own rule
   (`src/populace_dynamics/data/psid.py:97-109`).
2. From the cross-year individual file `ind2023er/IND2023ER.txt`: age,
   sequence number, relationship, weight and interview number for
   collection waves 2011, 2013 and 2015, resolved by the repository's
   label patterns (`src/populace_dynamics/data/panels.py:58-72`) through
   `panels.ind_person_period` (`panels.py:183-252`).
3. From family files `FAM2011ER`, `FAM2013ER` and `FAM2015ER`: interview
   number, head and spouse labor income, and their accuracy components,
   read by `family.read_family_labor` with its label verification
   (`src/populace_dynamics/data/family.py:703-775`).
4. For source identity only, the SHA-256 of every family file from the
   1968 wave through the 2015 wave and of `IND2023ER.txt` and
   `IND2023ER.sps`. These files are hashed, not parsed.
5. The pinned policyengine-us 1.752.2 `nawi.yaml`, read through the
   q\* selector's prefix reader, which stops at the 2010 key
   (`scripts/select_m6_qstar_train_only.py:513-585`). The check compares
   the prefix byte count, prefix hash and mapping hash with the pin at
   `scripts/select_m6_qstar_train_only.py:184-192`.
6. From the two committed 2010-boundary selection ledgers
   (`docs/analysis/m6_qstar_train_only_selection_results.json` and
   `docs/analysis/m6_rhostar_train_only_selection_results.json`), only
   these count fields of `boundaries["2010"]`: `support.n_full_anchor`,
   `support.n_domain`, `support.truth_support_rows`,
   `support.truth_support_rows_by_period`,
   `support.endpoint_support_rows`, `support.support_age_min`,
   `support.support_age_max`, `support.anchor_wave` and
   `fit_input_rows`. No other ledger field is read.

### Reduction at read time

`validity_frame` (`scripts/track_b_b0_1_counts.py:109-138`) replaces each
role's labor-income level with one flag, "below the PSID missing sentinel"
(`family.py:619`), and each accuracy code with "positive". No later step
sees a level. The unit test
`test_counts_are_invariant_to_valid_earnings_values`
(`tests/test_track_b_b0_1_counts.py`) replaces every valid level with an
arbitrary valid level and requires every output to stay identical.

### Definitions

These mirror the train-only selectors' 2010-boundary construction
(`scripts/select_m6_qstar_train_only.py:1410-1565`) and the family
earnings panel (`family.py:785-860`).

- **Reference year and collection wave.** Reference year *r* is collected
  at wave *r* + 1 (`family.py:843`). B2's reference years are 2010, 2012
  and 2014; its collection waves are 2011, 2013 and 2015.
- **Full anchor.** Persons with sequence 1-20 and positive weight at the
  2011 wave (`select_m6_qstar_train_only.py:1416-1428`). Their 2011
  weight is the fixed weight and their 2011 interview number the
  household identifier (`:1421`, `:1443`).
- **Valid row.** At wave *w*, a person present with sequence 1-20 who is
  head or reference person, or wife, spouse or partner, under the wave's
  relationship codes (`family.py:604-614`), with positive wave weight and
  that role's labor income below the sentinel (`family.py:821-859`).
- **Domain.** Full-anchor persons with a valid 2010 row. The selectors
  assert that this equals the fitted anchor set
  (`select_m6_qstar_train_only.py:1430-1441`).
- **Scored row.** A domain person's valid row at 2010, 2012 or 2014 whose
  collection-wave age lies in 25-64 (`src/populace_dynamics/engine/forward_earnings.py:66-67`;
  `select_m6_qstar_train_only.py:1444-1463`). Cohorts are prime (25-44)
  and older (45-64) by collection-wave age (`m6_cells.py:90`).
- **Level cells.** Scored rows at 2012 and 2014 pooled, by cohort
  (`m6_cells.py:491-512`).
- **Change pairs.** Persons with scored rows at both years of a two-year
  step (2010-2012, 2012-2014), counted per cohort when both rows share the
  cohort, and pooled; and the four-year pair 2010-2014, pooled
  (`m6_cells.py:513-586`).
- **Dispositions.** At 2012 and at 2014, every domain person receives
  exactly one label from `DISPOSITIONS` (`track_b_b0_1_counts.py:73-84`),
  in precedence order: scored; valid row with age outside 25-64; head or
  spouse with earnings at the sentinel; present with no family record;
  present in another relationship; present with non-positive weight;
  institution (sequence 51-59); moved out (71-80); died (81-89); not in a
  responding family. Sequence groups follow
  `docs/design/psid2010-cohort.md:17-28`.
- **Entrants not scored.** Persons outside the domain with a valid row
  and collection-wave age 25-64 at 2012 or 2014, split by whether they
  are in the 2011 full anchor.
- **Assigned or edited rows.** Scored rows whose role accuracy code is
  positive (`family.py:239-306`). This is a data-quality count, not an
  earnings value.
- **Effective sizes.** For each set of rows, the Kish size
  (Σw)² / Σw² and the cluster-worst size (Σw)² / Σ_c W_c², where W_c is
  the fixed-weight total of household *c*
  (`track_b_b0_1_counts.py:219-247`). The cluster-worst size is the
  effective size if every row in a 2011 household were perfectly
  correlated, so the true effective size lies between the two for any
  non-negative within-household correlation.

### Power quantities (no outcome enters)

`power_record` (`track_b_b0_1_counts.py:598-696`) computes:

1. **M6 floor rule.** For a floor-derived tolerance
   round(mean + 3 sd, 3) on a half-normal half-split score, the ratio of
   tolerance to the half-split sigma is √(2/π) + 3√(1 − 2/π). It reports
   the per-cell pass probability 2Φ(ratio) − 1 of M6's faithful-candidate
   operating characteristic (`m6_cells.py:701-734`), the 4-of-5 gate
   probability for 1, 6 and 16 cells, and the largest uncapped surface
   that keeps that probability at 0.90 or above.
2. **§5.2 bound rule.** A cell passes when its gap plus z\* times its
   standard error is within tolerance, with z\* the Bonferroni critical
   value over *m* cells at 95%. A faithful cell passes with probability
   2Φ(tol/se − z\*) − 1, which reaches 0.90 when
   tol/se ≥ z\* + Φ⁻¹(0.95). It reports that ratio for *m* = 1, 6 and 16,
   the pass probability at the M6 floor tolerance under M6's
   gap-sigma basis, and the *k* a floor tolerance would need.
3. **Monte Carlo.** The smallest number of draws *K* with
   se/√K < tol/10 when the tolerance is the M6 floor tolerance, on full
   and on half support.
4. **§5.3 earnings limits on B2's support.** For participation at 3
   percentage points, the worst-case (p = 1/2) effective size needed;
   for quantiles at 10%, the largest log-earnings SD a log-normal
   planning model allows at each cohort's effective size; and for
   persistence correlations at 0.05, the effective positive-pair size
   needed and the positive share it implies. Each uses the bound rule
   with *K* = 20 draws and ignores estimation uncertainty, so each is a
   necessary condition, not a sufficient one.

### Output and stop rules

- The script writes one exclusive file,
  `docs/design/track_b_b0_1_counts.json`, and refuses to overwrite a file
  or write under `runs/` (`track_b_b0_1_counts.py:849-858`). The record
  carries the repository head, the script's SHA-256, every opened PSID
  file's SHA-256 and the hashes in input 4.
- It runs once, from a clean worktree at the commit that adds this
  protocol. If it fails, the failure is published and the protocol is
  revised in a new, dated section before any rerun.
- No definition above changes after counts are seen. A change is a new
  protocol version, recorded as such, with the reason.
<!-- protocol:end -->
