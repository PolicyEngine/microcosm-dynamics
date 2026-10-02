# Track B B0.1: source, exposure, access and power audit for B2

**Status: audit record for B2, revision 1 (2026-09-29). It is a partial
freeze, and B2 cannot register on it.** The structural-audit protocol at
the end of this file was committed and pushed at `e51216f` before any
count ran. The count script then ran once, from a clean worktree at that
commit, and wrote `docs/design/track_b_b0_1_counts.json`. Every count
below comes from that file unless another source is cited.

Revision 1 answers the blinded review of the first version (`94623ee`).
It changes no count and no byte of the protocol. It adds three things:

- a mechanical exposure inventory,
  `docs/design/track_b_b0_1_exposure_inventory.json`, written once by
  `scripts/track_b_b0_1_exposure_inventory.py` from a clean worktree at
  `de08c69`;
- a power analysis that names its scoring basis for every figure
  (`scripts/track_b_b0_1_review_power.py`);
- an eighth question for Max.

Section 15 lists each review finding and what changed.

**Revision 2 (2026-09-30, after Max's rulings d693 and d622).** The
post-ruling addendum, `docs/design/track_b_b0_1_addendum.md`, freezes
elements 5-9 and the planning values. This file takes only the
corrections that round 2 of the blinded review (N1-N7) and d693 asked
for: the summary's side-A sentence (N1), the floor-equality claims (N2),
Q2's cost and its headroom, which is per cell (N3, d693), one citation
(N4), the inventory's scope (N5), the pinned-figure claim and two bands
(N6) and the wage vintage's element (N7). Section 15.5 lists them.
After the addendum's planning-value run, sections 1, 11 and 12 also say
that the "upper bound" standard errors are reference points, not
bounds. No count, protocol byte or recommendation
changed.

Verification class: **source audit** (design §3.2, line 144). It admits
nothing scientific. Before B2 registers, the design requires three more
things:

- a frozen record of all ten §5.2 elements plus the named power
  procedure (design line 288). This record freezes four elements and
  records a fifth; the addendum freezes the rest after Max's rulings
  (section 2);
- a blinded review of prospective feasibility and power (design §3.1
  row B0, line 120);
- a B1 replay that clears B2's dependency (line 121). Max ruled in d622
  (2026-09-30) that a B1 v2 "reconstructed reproduction" pass may
  unlock B2, with the weaker label carried into B2's registration
  (`docs/design/track_b_b1_v2_amendment.md:75-79`).

This record put eight questions to Max (section 12). Each states the
facts, the options and a recommended default. None is decided here; Max
ruled on all eight in d693, and the addendum records the rulings.

"The design" means `microcosm-launch-evidence/dynasim-parity-20260909/trackb-design-20260928.md`
(revision 3), which sits outside this repository. Max approved its §10
defaults in d515 on 2026-09-28. Design line numbers refer to that file.

## 1. Summary

- **Sources.** B2 reads the PSID family files and the cross-year
  individual file already staged for M6. Every variable resolves under
  the repository's label checks. The codebooks define head and spouse
  labor income the same way in all three waves, except that the 2015
  head entry no longer lists market gardening among its components
  (section 4). The pinned 2010 NAWI prefix in policyengine-us 1.752.2
  matches the repository pin byte for byte.
- **Exposure.** Reference years 2012 and 2014 offer no unused
  holdout.
  - The q\* and ρ\* selectors scored each pseudo-boundary b on reference
    years b, b + 2 and b + 4. So boundary 2010 scored realized 2012 and
    2014, and boundary 2008 scored realized 2012, on B2's six
    M6-retained cells.
  - Both public ledgers publish the floors, the truth moments and the
    projected moments for every q and ρ rung at both boundaries.
    Candidate 3's exact law (q = 0.55, ρ = −0.60) is one of the rungs.
  - A scan of every tracked file finds 20 files that hold or may state
    such content (section 5).
- **Population.** The domain is 13,542 heads and spouses with a valid
  2010 row, drawn from 23,134 persons present with positive weight at
  the 2011 wave. B2 scores 10,165 rows at 2012 and 9,310 at 2014.
  These counts equal the committed selector ledgers' counts exactly
  (section 7).
- **Power under M6's operating characteristic.** A surface of 6 uncapped
  floor-derived cells has p_gate = 0.974 and one of 16 has 0.859. So the
  full battery cannot clear 0.90 without pruning (section 11.1).
- **Power under §5.2's bound rule.** The answer depends on the scoring
  basis and on the gap's standard-error convention, and the design fixes
  neither (Q2). Take a faithful cell at M6's k = 3 tolerance, before
  estimation error, for m = 1, 6 and 16 cells:
  - under M6's convention it passes with probability 0.48, 0 and 0;
  - on side-A scoring, with probability 0.898, 0.662 and 0.479 at the
    reference standard error, so at that standard error it misses 0.90
    even for one cell;
  - on full-support scoring, with probability 0.998, 0.986 and 0.967 at
    its reference standard error.

  The reference standard errors are reference points, not bounds
  (section 11).

  Estimation error lowers all three, and this audit does not bound it
  (section 11.2).
- **§5.3 limits.** Their text names B3's bands, not B2 (Q4). Even
  applied to B2, sample sizes alone do not settle them. Each turns on a
  planning value that this audit may not compute from 2012 or 2014: a
  participation rate, a dispersion, or a correlation and its tails (Q5).
  The first version's claim that lag-2 persistence at 0.05 is infeasible
  at every family size is withdrawn (section 11.3).
- **Freeze status.** Elements 1-3 and 10 are frozen and element 4 is
  recorded. Elements 5-9 and the planning values wait on Q1-Q5 and Q8.
  A post-ruling addendum, with its own blinded review, freezes the rest
  before B2 registers (section 13).
- **Eight open questions** need Max's ruling (section 12).

## 2. The §5.2 elements and where this record stands on each

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
| 2. Variables | 4 | Frozen; codebook concept check added in revision 1 |
| 3. Population | 7 | Frozen |
| 4. Exposure history | 5 | Recorded from a mechanical inventory; its consequences need Q1 and Q8 |
| 5. Holdout partition | 8 | Open. Estimation and evaluation years are fixed; the split unit needs Q3; no unused partition exists (Q8) |
| 6. Critical cells | 9 | Open. Candidate family listed; surface needs Q1 |
| 7. Numerical tolerances | 9 | Open. Floor-derivation rule drafted; the role of §5.3 needs Q4 |
| 8. Uncertainty treatment | 10 | Open. Needs Q2 and Q3 |
| 9. Pass conjunction | 10 | Open. Inherited M6 conjunction recorded; needs Q2 |
| 10. Reference dates vs availability | 4.3 | Frozen |
| Named power procedure | 11 | Named; planning values need Q5 |

The statuses above are as of revision 1. Since d693, the addendum's
table supersedes this one: it marks all ten elements and the power
procedure frozen, with elements 5-9 in the addendum.

**Wage vintage (N7).** Element 1, the source release, freezes B2's wage
vintage: the policyengine-us 1.752.2 `nawi.yaml`, realized through 2010,
with later years from the fitter's log-linear projection over 2001-2010
(section 3). It is the series as later revised, not a 2011-era release.
Element 10 records that availability gap. The choice follows the code
B2 transports and the selectors, and design line 150 already scopes B2
as "Not a 2010-vintage forecast", so it needed no ruling.

"Frozen" means fixed by this record, subject to the blinded review. The
record is therefore a partial freeze. Design line 288 says "A gate cannot
register until its record is frozen", so this record supports the
questions in section 12 and the post-ruling addendum, not B2's
registration.

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

The loader treats both years' spouse income as one concept.

**Codebook concept check (revision 1).** Revision 1 read the codebook
definitions of the six labor-income variables in the staged
`FAM2011ER`, `FAM2013ER` and `FAM2015ER` codebooks. Every digit was
masked and each entry was cut off before its frequency table
(section 14). What the definitions say:

- All six define the concept as labor income "Excluding Farm and
  Unincorporated Business Income". Each notes that farm income and the
  labor portion of business income are not included, and that missing
  data were assigned.
- `ER52249` and `ER58050` are the wife's labor income. `ER65244` is the
  "Spouse's/Partner's". The 2011 and 2013 wife entries list no
  components. The 2015 spouse entry lists wages and salaries, bonuses,
  overtime, tips, commissions, professional practice or trade,
  additional job income and miscellaneous labor income.
- The head entries `ER52237` (2011) and `ER58038` (2013) list those
  components plus market gardening. `ER65216` (2015) does not list
  market gardening.

The concept therefore reads the same across B2's window. The one
difference is that market gardening is absent from the 2015 component
lists. Whether the 2015 instrument dropped or moved that component was
not checked. B2's registration should record this check, definitions
only.

These codebook entries also print unweighted frequency tables, zero
counts included. For the 2013 and 2015 waves those tables describe B2's
target years, so a concept check must stop before them (Q6). No
pre-1994 concept seam lies inside B2's window (`family.py:25-32`).

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
4. **Train-only selection at pseudo-boundaries 2008 and 2010, on B2's own
   estimand.** The q\* and ρ\* selectors refit the complete forward law
   on rows dated ≤ b. They then scored reference years b, b + 2 and
   b + 4 (`select_m6_qstar_train_only.py:1444`): level cells on b + 2
   and b + 4, and change cells over b → b + 2 → b + 4 (`:1475-1476`).
   The six cells are `earn_p10.prime`, `earn_dlog_mean.prime`,
   `earn_dlog_sd.older`, `earn_mob_h1_diag`, `earn_autocorr_lag2` and
   `earn_zero_rate.older`.
   - **Boundary 2010** projected 2010 → 2012 → 2014 and scored the six
     cells against realized 2012 and 2014 earnings, on the support B2
     would use (`docs/design/m6_projection_engine.md:1076-1140`;
     `select_m6_qstar_train_only.py:1410-1565`).
   - **Boundary 2008** projected 2008 → 2010 → 2012 and scored the same
     cells on realized 2010 and 2012 levels and on the 2008 → 2010 →
     2012 changes. Its 2012 level is one of B2's two level years, and
     its 2010 → 2012 change is one of B2's two change steps. Both ledgers
     record a `2012` key in `boundaries["2008"].support.truth_support_rows_by_period`.
   - **Boundary 2006** scored reference years 2006 to 2010, all inside
     B2's estimation window. It touches no B2 target year.
   - The objective J(q) summed standardized squared scores over
     boundaries 2006, 2008 and 2010 (`m6_projection_engine.md:1133-1140`),
     and q = 0.55 was selected on it
     (`docs/design/m6_candidate3_program.md:202-228`). The ρ\* selection
     did the same over ρ rungs at fixed q = 0.55
     (`m6_projection_engine.md` §2.7.8.5, from line 1415). Both ledgers
     keep every rung's block at all three boundaries, so candidate 3's
     law (ρ = −0.60) has 2008 and 2010 blocks.
5. **F1 mechanism diagnostic.** At boundary 2010 with q = 0.55, it
   compared projected and realized 2012 and 2014 mean Δlog earnings
   (prime) and lag-2 autocorrelation, draw by draw. It carries the caveat
   that "the evaluated waves sat inside q\*'s selection evidence"
   (`m6_candidate3_program.md:237-253`). The ρ\* ledger also carries a
   `train_f1_analog_disclosure` block for every ρ rung at each of the
   three boundaries.
6. **The paper.** Figure `fig-m6-frontier` plots q\* objective
   contributions summed over the three pseudo-boundaries, 2008 and 2010
   included (`paper/paper.qmd:2238-2248`;
   `paper/figures/m6_q_frontier.svg`;
   `scripts/build_paper_figures.py:571-625`).
7. **Prose restatements.** `m6_projection_engine.md` §2.7.8 (from line
   1258) states boundary-2010 diagnostic outcomes in prose. The blinded
   review reports a standardized cell score, a 2012 wage-index projection
   error and a persistence diagnostic at lines 1266, 1290 and 1311.
   Revision 1 confirmed only that those lines name boundary 2010 and
   carry decimal numbers; it did not read them. The inventory (section
   5.5) finds further value-bearing ranges in the same file and in 15
   other text files, among them the candidate-2 and candidate-3
   programs, both lock addenda and the q\* and ρ\* analysis notes.
8. **Marital selectors at pseudo-boundaries 2008 and 2010.** The
   first-marriage and remarriage selectors also used boundaries 2006,
   2008 and 2010 (for example `docs/analysis/m6_first_marriage_c_selection.md`).
   They bear on B4, not on B2's earnings surface, and are recorded here
   for B0.2.

### 5.2 What the committed JSON artifacts contain for boundaries 2008 and 2010

The first version read the artifacts' key names, metadata strings and
count fields. Revision 1 read the key names of the 2008 blocks and the
rung blocks. Neither read a value field. Section 15.2 records both as a
deviation from protocol input 6.

| Artifact | SHA-256 | Merged | Content at boundaries 2008 and 2010 (by field name) |
|---|---|---|---|
| `docs/analysis/m6_qstar_train_only_selection_results.json` | `d25b8e15…25bb` | #255, 2026-07-18 | Per boundary: the 100-seed floor (mean, SD, realized σ, events) and full-support truth moments for the six cells, and half-split scores and event counts at floor seeds 0-4 for all 21 earnings cells. Per boundary for each of 21 q rungs: the refit's fit record, projected aggregates for the six cells (all 20 draws and each half of them), a per-draw summary with moment ranges, truth moments, regeneration checks and objective contributions, delete-one included |
| `docs/analysis/m6_rhostar_train_only_selection_results.json` | `db7fe835…63ff` | #273, 2026-07-23 | The same for 17 ρ rungs at fixed q = 0.55, ρ = −0.60 (candidate 3's law) included. Each rung also has per-draw transition-pair counts and a `train_f1_analog_disclosure` block at each boundary, and the ledger has a ρ = 0 equivalence preflight at each boundary |
| `docs/analysis/m6_c3_f1_mechanism_diagnostic_results.json` | `dcd1bf35…a0bb` | #271, 2026-07-22 | Boundary 2010 only: per-draw projected and realized mean Δlog (prime) and lag-2 autocorrelation at q = 0.55 |

The 21 cells in the seed detail are the 16 gateable cells plus 5
report-only cells (section 9). The q\* reducer states that it removed the
per-draw projected records
(`m6_qstar_train_only_selection_results.json`, field `reducer.removed`).
This audit did not check which cells the removed records covered.

Among tracked JSON artifacts, these three are the only ones with
boundary-keyed earnings blocks or `pseudo_boundary` fields at 2008 or
2010; the others the inventory finds are marital. A fourth JSON file,
`docs/forecasts/timeline_ledger.json`, holds prose strings that name a
boundary year or the train-only selector next to a number. Prose files
are covered in section 5.5.

The repository is public, so all of these have been public since they
merged.

### 5.3 Who has seen them

- **The lanes that produced them.** PRs #255, #271 and #273 were merged
  under Max Ghenis's GitHub account.
- **Anyone reading the public repository or paper figure 5.**
- **The Track B design's authors.** They state that 2012/2014 were
  selection evidence (design lines 121, 150, 333), and that outcomes
  after all three pseudo-boundaries were used for selection (line 55).
  Their current-run inventory (design lines 507-553) lists none of these
  artifacts, so this audit has no evidence that they read the values.
- **This audit's authors.** See section 14.

### 5.4 Consequences for B2

- **No unused partition exists on B2's target years.** Design line 286:
  "Previously inspected outcomes remain regression evidence". §3.2
  already classes B2 as retrospective regression (design line 150).
- **That meets the trigger of `EXPOSURE_UNRESOLVED`.** Design line 455
  triggers the condition when "B0 cannot establish access or an unused
  partition". It stops "That admission and its dependants", and "A
  registered fallback may proceed only with its own narrower scope".
  B2's dependants are H and B3L (design line 121). Whether B2's
  retrospective-regression class answers the condition, or it blocks H
  and B3L until a narrower fallback registers, is Q8.
- **The six cells' person-split floor already exists.** Under a person
  split (Q3 option (a)), B2's floor for the six M6-retained cells is by
  construction the floor the selectors published. The constructions
  match: same anchor, domain, split order, seeds, reducer, years and
  fixed weights (`select_m6_qstar_train_only.py:1416-1479`). Under the
  household split that d693 adopted (Q3 option (b)), B2's gating floor
  is new and unpublished, and the person-split floor becomes a
  non-gating reproduction check (N2). The
  selectors published candidate-3-law outcomes on the same cells in the
  same record, at boundary 2010 and, for realized 2012, at boundary
  2008.
- **What the ordering rule can still bind.** "Floors derived before
  candidate outcomes" (design line 332) can bind B2's own registered run,
  but not what is already public (Q1).

### 5.5 Mechanical exposure inventory

The first version built its exposure list by hand, and the review found
it incomplete. Revision 1 replaces the list with
`scripts/track_b_b0_1_exposure_inventory.py`. It was committed at
`de08c69` and run once from a clean worktree at that commit. It scanned
1,647 tracked files, leaving out the eight B0.1 files. It searched for
six pattern families:

- a pseudo-boundary;
- the train-only phrase;
- a boundary year (2006, 2008 or 2010);
- the q\* or ρ\* selector names, or J(q) and J(ρ);
- the F1 mechanism diagnostic;
- the frontier figure.

It records no line content, and no JSON value other than the boundary
years. Its rules are:

- **Targets.** A boundary touches B2's targets when one of its scored
  periods b, b + 2 or b + 4 is 2012 or 2014. That makes boundaries 2008
  and 2010 the relevant ones.
- **JSON.** A JSON file is value-bearing when it has one of three
  things:
  - a non-marital block keyed by 2008 or 2010;
  - a `pseudo_boundary` field equal to 2008 or 2010;
  - a string that names the selection next to a decimal number or a
    target year.
- **Text.** A text range (hit lines ± 5) is value-bearing when it names
  the selection and contains a decimal number or a target year. The
  train-only phrase alone does not count as naming the selection.
- **Marital.** Paths or keys about marriage, remarriage, widowhood,
  divorce or dissolution are marital, which is B4's surface.
- **Code.** Python source under `src/` and `scripts/` computes outcomes
  rather than recording them, so it is listed as code. Test modules are
  scanned as text.

The inventory covers tracked files only (N5). It does not cover the
threads of PRs #255, #271 and #273, the registration comments on issue
#42, or the launch-evidence directory; the Q6 reviewer brief excludes
those separately, and d693's ruling leaves every one of the 20 listed
files out of the review root whole, not by line range.

The result is 20 value-bearing files, 45 marital, 24 code and 31 that
only mention a phrase. Section 15.4 lists the 20 value-bearing files and
the parts a blinded reviewer should not open. The rules are
deliberately broad: a range that names q\* next to 0.55 counts, so some
listed ranges state only candidate 3's public parameters.

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

## 8. Holdout partition (element 5, open)

- **Estimation.** Earnings rows with reference year ≤ 2010
  (`forward_earnings.py:1021-1024`), fitted at ages 25-64. NAWI is
  realized through 2010 and projected after it.
- **Evaluation.** Realized 2012 and 2014 rows on the 2010 domain,
  collection-wave ages 25-64.
- **Inherited M6 structure.** Gate seeds 0-4 each choose a 50% person
  split "side A" and score it (`src/populace_dynamics/harness/m6_scoring.py:394-425`,
  `:624-733`). Floor seeds 0-99 split the full anchor into halves
  (`m6_cells.py:614-689`).
- **Split unit, open.** Whether floor and gate seeds split by person, as
  in M6, or by 2011 household is Q3. Until it is ruled, the partition is
  not frozen.
- **No unused partition.** Every evaluation row lies in the years
  section 5 lists as exposed. "'Later' or 'external' does not establish
  an unused holdout" (design line 286). What that means for B2's
  dependants is Q8.

## 9. Cells and floor-derivation rule (elements 6 and 7, open)

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
are the most exposed: the ledgers hold candidate-3-law outcomes for them
at boundaries 2008 and 2010 (section 5.2). The other ten have published
five-seed floor detail at both boundaries but no published candidate
outcome.

### 9.2 Draft floor-derivation rule, to run before any B2 candidate outcome

This carries forward M6's discipline (design lines 330-333) with B2's
years. It uses no 2016/2018 tolerance. The post-ruling addendum freezes
it (section 13).

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
   the operating characteristic of section 11 on the ruled basis (Q2)
   and requires p_gate ≥ 0.90 (`m6_cells.py:64`). It also applies the
   vacuity guards: not every tolerance at its cap, and at least
   `MIN_GATED_CELLS_FOR_POWER` cells where the ruling keeps that guard
   (`m6_cells.py:67`).
8. The builder publishes the floor artifact and its hash. B2's candidate
   runs only after the floor is committed.

Under a person split, the six-cell floor must equal the published
selector floor, and the five-seed detail must equal the published seed
detail. A B2 build can test that differentially. That equality is also
why a person-split six-cell floor is not new information (section 5.4).
Under the household split d693 adopted, the gating floor is new; the
person-split floor is kept as the non-gating differential check (N2).
A separate comparator runs that check, not the floor builder, which
reads no selection ledger (addendum, element 5).

## 10. Uncertainty treatment and pass conjunction (elements 8 and 9, open)

**Inherited M6 rule** (design §5.4, lines 330-333):

- for each gate seed, score the mean of K = 20 draws on side A against
  side-A truth;
- a seed is valid when no gated cell has an undefined draw and every
  gated cell's K draws are not all identical (regenerated); a valid seed
  passes when every gated cell is within tolerance;
- the gate passes when all five seeds are valid and at least 4 of them
  pass (`m6_scoring.py:35-38`, `:713-751`). Revision 1 left out the
  all-seeds-valid condition; revision 2 restores it.

Uncertainty enters only through the half-split floor and the 4-of-5
conjunction.

**§5.2 rule** (design lines 299-304):

- each critical cell's simultaneous 95% bound, Bonferroni over the
  registered family, must lie within its tolerance;
- resampling respects survey design and family clusters;
- Monte Carlo error must be below a tenth of the tolerance;
- insufficient precision is inconclusive.

The two rules conflict in two ways, quantified in section 11:

- **The pass rule.** At the k = 3 floor tolerance, the bound rule's pass
  probability depends on the scoring basis and on the gap's
  standard-error convention. Under M6's convention, and on side A at the
  upper-bound standard error, it falls below 0.90 before any estimation
  error (Q2).
- **The split unit.** M6 splits earnings by person
  (`gates.yaml:5533-5537`), which can place spouses in different halves.
  §5.2 asks resampling to respect family clusters. B2's 13,542 domain
  persons live in 8,907 2011 households, each with its domain head, so
  all 4,635 domain spouses share a household with a domain head. If no
  family holds more than one spouse or partner, 4,635 households hold
  two domain persons, and 9,270 persons (68%) sit in two-person
  clusters. The frozen record does not count persons per household, so
  that condition is stated rather than verified (Q3).

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
It uses no B2 outcome. Revision 1's figures come from
`scripts/track_b_b0_1_review_power.py`, which reads only the frozen
record's sample sizes and reuses the frozen script's functions;
`tests/test_track_b_b0_1_audit_record.py` pins every one, including,
since revision 2, the prose-only figures N6 listed.

**Gap conventions.** σ is a cell's half-split floor σ, and K = 20.

- **M6's convention.** A faithful cell's gap has standard error σ. M6's
  operating characteristic treats the gap this way
  (`m6_cells.py:701-734`), and so did the frozen record's bound-rule
  column.
- **Side A.** This is M6's scoring (section 10). A half's statistic has
  variance σ²/2, and the mean of K draws adds 1/K of that. So the gap's
  survey-plus-simulation standard error was taken to be at most
  σ·√((1 + 1/K)/2) ≈ 0.725 σ.
- **Full support.** The same on the whole domain:
  σ·√(1 + 1/K)/2 ≈ 0.512 σ.

These were offered as upper bounds, on the reasoning that side-A truth
and side-A projections start from the same persons' 2010 anchors, so the
part of a statistic's sampling variation that the anchors explain
cancels in the gap. A design-based resampled gap standard error would measure how much
cancels, but it needs outcome data (Q5). No convention includes
estimation error.

*Revision 2 correction.* These are not bounds. Over household resamples
with the law and paths fixed, the gap's variance is Var(T) + Var(P̄) -
2 Cov(T, P̄), and it stays within the figures above only if the
covariance offsets the projected statistic's own resampling variance, up
to Var(T)/K. Nothing guarantees that. The addendum's planning-value run
measured the full-support ratio r, the gap standard error over
σ·√(1 + 1/K)/2, at the 2006 pseudo-origin: it is above 1 for seven of
the 16 cells, up to 1.21 for `earn_p10.prime` (addendum section 10).
The figures on these bases are reference points.

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

A faithful cell passes when its gap plus z\* standard errors lies within
the tolerance. At M6's k = 3 floor tolerance (2.606 σ), before
estimation error, the pass probability is:

| m | z\* (Bonferroni 95%) | Needed tol/se | M6 convention (se = σ) | Side A (se = 0.725 σ) | Full support (se = 0.512 σ) |
|---:|---:|---:|---:|---:|---:|
| 1 | 1.960 | 3.605 | 0.482 | 0.898 | 0.998 |
| 6 | 2.638 | 4.283 | 0.000 | 0.662 | 0.986 |
| 16 | 2.955 | 4.600 | 0.000 | 0.479 | 0.967 |

The k a floor tolerance round(mean + k SD) needs for 0.90 power, before
estimation error:

| m | M6 convention | Side A | Full support |
|---:|---:|---:|---:|
| 1 | 4.66 | 3.01 | 1.74 |
| 6 | 5.78 | 3.82 | 2.32 |
| 16 | 6.31 | 4.21 | 2.59 |

- **M6's convention.** The pass probability falls from 0.48 at m = 1 to
  0.28, 0.17, 0.09 and 0.02 at m = 2 to 5. From m = 6, z\* exceeds 2.61,
  so the bound rule cannot pass at all. The first version reported only
  this column. It is one end of the range, not the answer.
- **Side A.** The conflict at m ≥ 6 is real but not total. At the
  reference standard error there is no room for estimation error at
  any m. The largest estimation variance compatible with 0.90 power is
  negative: −0.4%, −29% and −39% of the gap variance at m = 1, 6 and
  16. The shared-anchor reduction could make room; its size needs
  outcome data.
- **Full support.** For one cell, the bound rule reaches 0.90 if
  estimation error adds at most 99%, 41% and 22% of the
  survey-plus-simulation gap variance se_full²·(1 + 1/K) at m = 1, 6 and
  16. Those are per-cell figures (revision 2): for the whole gate, with
  every cell required to pass, the room is 99%, 2.8% and none. The first version gave these as
  104%, 43% and 23% "of that variance" without naming the reference,
  which was se_full² alone.
- **Estimation error.** Nothing here bounds it, and its size decides
  whether any basis clears 0.90 (Q2).

### 11.3 §5.3 earnings limits evaluated on B2's support

§5.3's earnings row (design line 312) was written for B3's bands at
ages 62-69. Whether it applies to B2 is Q4. This section shows what it
would demand.

Each figure uses the bound rule with K = 20 and no estimation term.
Adding estimation error can only raise a requirement, so in that
respect the figures understate it. But each also fixes a planning
quantity at a worst case or a normal-theory value, and in that respect
it can overstate the requirement. The figures are therefore neither
necessary nor sufficient conditions. They are bounds conditional on the
stated planning value, and the first version was wrong to call them
necessary conditions.

Side-A sizes are half the recorded full-support sizes. Under a 50%
person split that is about the expected Kish size. It underestimates the
household-worst size, because side A keeps at least half of it.

**Participation, 3 percentage points.** A cell with participation rate
p needs an effective size of N(m)·4p(1 − p). N(m) = 3,790, 5,351 and
6,172 for m = 1, 6 and 16 is the worst case, p = 1/2. The table gives
the smallest p ≥ 1/2 at which each size suffices. The cell is feasible
at any rate at least that far from 1/2, on either side. "Any" means
every p.

| Cohort and basis | Kish n_eff | Smallest feasible p (Kish), m = 1 / 6 / 16 | Household-worst n_eff | Smallest feasible p (household-worst), m = 1 / 6 / 16 |
|---|---:|---|---:|---|
| Prime, full support | 6,122 | any / any / 0.545 | 2,303 | 0.813 / 0.877 / 0.896 |
| Older, full support | 5,952 | any / any / 0.594 | 2,100 | 0.834 / 0.890 / 0.906 |
| Prime, side A | 3,061 | 0.719 / 0.827 / 0.855 | 1,152 | 0.917 / 0.943 / 0.951 |
| Older, side A | 2,976 | 0.732 / 0.833 / 0.860 | 1,050 | 0.925 / 0.948 / 0.955 |

So "fails under the household-worst bound" holds only for participation
rates in a band around 1/2. For the prime cohort the band runs from
about 0.19-0.81 (full support, m = 1) to about 0.049-0.951 (side A,
m = 16); for the older cohort, from about 0.17-0.83 to about
0.045-0.955. (Revision 1 paired the prime cohort's first endpoint with
the older cohort's second; N6.) Side-A Kish sizes also fail in a band:
about 0.28-0.72 (prime) and 0.27-0.73 (older) at m = 1. Where B2's
rates lie is a planning value (Q5).

**Positive-earnings quantiles, 10% (tolerance ln 1.1).** Under a
log-normal planning model with every row positive, the largest
log-earnings SD a cell tolerates at m = 6 is:

| Cohort | p10 or p90, full support (Kish / worst) | p10 or p90, side A | p50, full support | p50, side A |
|---|---|---|---|---|
| Prime | 0.99 / 0.61 | 0.70 / 0.43 | 1.36 / 0.83 | 0.96 / 0.59 |
| Older | 0.98 / 0.58 | 0.69 / 0.41 | 1.34 / 0.79 | 0.95 / 0.56 |

With positive share π, each limit scales by √π. Other family sizes are
in the counts file. Feasibility turns on a dispersion planning value
this audit may not compute from 2012 or 2014 (Q5).

**Persistence correlation, 0.05.** The first version used the bound
se(r) ≤ 1/√n and found that 5,458, 7,705 and 8,887 effective positive
pairs are required for m = 1, 6 and 16. The bound has two problems:

- Under normal theory se(r) = (1 − ρ²)/√n, so 1/√n is its value at
  ρ = 0. The figures above are therefore the largest normal-theory
  requirement, not a necessary condition.
- For heavy-tailed data the variance of r is larger by a fourth-moment
  factor λ. For elliptical distributions λ = 1 + κ, where κ is the
  kurtosis parameter. So se(r) can exceed 1/√n.

The requirement is N0(m)·λ·(1 − ρ²)² effective positive pairs, where
N0(m) is the figure above. With every pair positive, the cell is
feasible when ρ is at least the value shown ("any" means every ρ ≥ 0).
With positive-pair share s, replace n_eff by s·n_eff.

| Pairs and basis | Size | n_eff | Smallest ρ, λ = 1, m = 1 / 6 / 16 | Smallest ρ, λ = 2, m = 1 / 6 / 16 |
|---|---|---:|---|---|
| Lag 1 (two-year steps, pooled), full support | Kish | 11,369 | any / any / any | any / 0.38 / 0.45 |
| | household-worst | 3,825 | 0.40 / 0.54 / 0.59 | 0.64 / 0.71 / 0.73 |
| Lag 1, side A | Kish | 5,685 | any / 0.38 / 0.45 | 0.53 / 0.63 / 0.66 |
| | household-worst | 1,912 | 0.64 / 0.71 / 0.73 | 0.76 / 0.80 / 0.82 |
| Lag 2 (2010-2014), full support | Kish | 5,310 | 0.12 / 0.41 / 0.48 | 0.55 / 0.64 / 0.67 |
| | household-worst | 3,448 | 0.45 / 0.58 / 0.61 | 0.66 / 0.73 / 0.75 |
| Lag 2, side A | Kish | 2,655 | 0.55 / 0.64 / 0.67 | 0.71 / 0.76 / 0.78 |
| | household-worst | 1,724 | 0.66 / 0.73 / 0.75 | 0.78 / 0.82 / 0.83 |

Two published facts bear on λ and on the planning value without using
B2 data:

- **The 1/√n bound is not established for PSID earnings.** M6 v4's
  published 2016/2018 lag-2 floor has realized σ = 0.0333
  (`gate_m6_amendment_1_closed_domain_floors.md:70`). So a half's
  standard error was about 0.0236. That is at most 1/√n only if the
  weaker half held fewer than about 1,800 effective positive 2014-2018
  pairs. The recorded minimum weaker-half support is 5,636, which for
  this cell counts persons in the change frame (`m6_cells.py:584`,
  `:656-660`). That is an upper bound on pairs, so the published figures
  do not settle it. Nothing in the record shows
  that 1/√n bounds se(r) on real PSID earnings.
- **M6's σ as a planning value (Q5).** On full support, that σ implies a
  standard error of about 0.0167. Before estimation error, the bound
  rule at 0.05 allows at most 0.0135, 0.0114 and 0.0106 at m = 1, 6 and
  16. So lag-2 at 0.05 would need B2's effective positive-pair support
  to be 1.52, 2.14 or 2.47 times M6's on full support, and 3.03, 4.28
  or 4.94 times on side A. That points toward infeasibility. But it
  rests on a planning value, and on a ratio of the two supports that
  this audit has not measured.

**Withdrawn.** The first version said lag-2 persistence at 0.05 "cannot
be met on B2's support at any family size, even if every pair were
positive, under either effective size". It then called that a
`WEAK_POWER_OR_VACUITY` case needing prospective rescoping (design lines
445, 454). Both statements rested on the 1/√n bound, and both are
withdrawn. Whether any §5.3 limit is infeasible on B2's support is
decided by the planning-value ruling (Q5), and matters only if Q4
applies the limits to B2. Any rescoping still happens before any
candidate outcome.

### 11.4 What this analysis does not settle

- **Estimation uncertainty.** It is not bounded here. The fit uses
  321,500 rows dated ≤ 2010: that is the selectors' `fit_input_rows`,
  a count read from the ledgers.
- **Shared-anchor variance.** The side-A and full-support standard
  errors are reference points, not bounds (the revision 2 correction
  above). A design-based resampled gap standard error needs outcome
  data.
- **Planning values.** Participation rates, positive-earner shares,
  log-earnings dispersion, the lag-1 and lag-2 correlations with their
  fourth-moment factors, and the true household design effect (Q5).
- **The blinded review.** It has not run (Q6).

## 12. Open questions for Max

Each question gives the facts, the options and a recommended default.
The defaults are proposals; none is adopted here.

1. **Which cells does B2 gate, given the exposure in section 5?**
   - Facts:
     - The six M6-retained cells have public floors, truth moments and
       candidate-3-law outcomes at boundaries 2008 and 2010. Those cover
       realized 2012 at both boundaries and realized 2014 at 2010.
     - The other ten gateable cells have public five-seed floor detail
       at both boundaries and no published candidate outcome.
   - Options:
     - (a) the six retained cells, knowing B2 largely re-scores a
       published computation with new draw seeds;
     - (b) the 16-cell battery, pruned by a candidate-blind rule on
       B2's own floor, such as M6's ladder (`gates.yaml:5590-5599`).
       On M6's half-normal basis at most 12 uncapped cells clear 0.90;
     - (c) the ten cells with no published candidate outcome, pruned
       the same way;
     - (d) another candidate-blind rule.
   - **Recommended default: (b).** It is the floor, cap and power
     discipline that design §5.4 says B2 carries forward, and it picks
     cells without reference to any outcome. The six cells' exposure is
     disclosed, not used to choose. (c) is the choice if re-scoring
     published cells matters more than continuity with M6.
   - Related: does "floors derived before candidate outcomes" bind only
     B2's own registered run? **Recommended default: yes.** B2's floor
     builder is pinned and committed before B2's candidate runs, and
     the public selector floors are recorded as prior exposure.
2. **How do §5.2's bound rule and §5.4's M6 discipline combine?**
   - Facts: at the k = 3 tolerance, before estimation error, a faithful
     cell passes the bound rule as follows (m = 1, 6 and 16):
     - 0.48, 0 and 0 under M6's convention;
     - 0.898, 0.662 and 0.479 on side A;
     - 0.998, 0.986 and 0.967 on full support,

     each at the reference standard error of section 11, which is not a
     bound.

     The estimation term is unbounded (section 11.2).
   - Options:
     - (a) the M6 rule alone (half-normal operating characteristic, 4
       of 5 seeds), with the bound rule reported but not gating;
     - (b) the bound rule on full-support scoring, keeping the k = 3
       floor tolerance. The gap standard error would come from a
       design-based, household-clustered resampling, with a registered
       bound on estimation variance;
     - (c) the bound rule on side-A scoring with a larger k, about 3.8
       at m = 6 before estimation error;
     - (d) another composition.
   - **Recommended default: (b).** §5.2 requires the bound rule for
     every empirical gate. Full support is the only basis on which the
     k = 3 floor tolerance leaves room for estimation error: 41% of the
     gap variance at m = 6.
     - **Revision 2 correction (d693).** The 41% is room for one cell.
       The gate passes only when every gated cell passes, and at the
       gate level the room is 2.8% of the gap variance at m = 6 (16.0%
       at m = 4, 8.4% at m = 5, none at m = 16). Under M6's ladder a
       surface of four or five cells is reachable only if whole concept
       families have no eligible cell. Before estimation
       error the whole bound rule passes with probability 0.917 at 6
       cells and 0.584 at 16. The addendum recomputes power at the gate
       level.
     - **Cost (N3).** Scoring on full support keeps the half-split k = 3
       tolerance, so the tolerance is about 5.1 standard errors wide
       instead of about 3.6 on side A: about 1.4 times wider. That costs
       sensitivity to a misspecified candidate.
     - The default holds only if the post-ruling addendum bounds the
       estimation term below that headroom, from ≤ 2010 data. If it
       cannot, the gate is `WEAK_POWER_OR_VACUITY` and is rescoped
       before any candidate outcome.
     - (b) also replaces M6's side-A seed conjunction, which design
       §5.4 says B2 carries forward. So it needs Max to rule that the
       bound rule takes precedence.
3. **Should the floor and gate seeds split by person, as M6 does, or by
   2011 household, as §5.2's "respects family clusters" implies?**
   - Facts: all 4,635 domain spouses share a household with a domain
     head (section 10). The worst-case household design effect cuts
     effective sizes by a factor of 1.5 to 3.0.
   - Options: (a) by person; (b) by 2011 household.
   - **Recommended default: (b).** §5.2 requires resampling to respect
     family clusters, and a household split lets the floor σ carry the
     cluster correlation instead of ignoring it.
4. **Do §5.3's earnings limits apply to B2 at all?**
   - Facts:
     - §5.3's earnings row names B3's bands at ages 62-69, with B3L as
       regression evidence.
     - §5.4's B2 row specifies floor-derived tolerances.
     - If the limits did apply, sample sizes alone would not settle
       them. Participation fails under the household-worst bound only
       for rates near 1/2, and on side A at Kish sizes in a band of
       about 0.28-0.72 at m = 1 (N6). Persistence and quantile
       feasibility depend on planning values (section 11.3).
   - Options: (a) no; (b) yes, as caps on B2's floor-derived
     tolerances.
   - **Recommended default: (a),** on the text of §5.3 and §5.4. Section
     11.3's figures then pass to B0.2 as inputs to B3's power review.
5. **Which planning values may the B2 registration use?** The values
   needed are participation rates, positive shares, dispersion, the
   correlations and their fourth-moment factors, the household design
   effect and an estimation-variance bound.
   - Options:
     - (a) B2's own ≤ 2010 estimation window, computed under a new,
       frozen, outcome-blind protocol version;
     - (b) M6's published 2016/2018 floor. It is not B2 data and is
       available now, but it covers only the six retained cells, and
       M6's population and years;
     - (c) none, keeping this audit's conditional bounds, which cannot
       decide feasibility.
   - **Recommended default: (a), with (b) as a cross-check where a cell
     exists.** Rows dated ≤ 2010 are already in B2's estimation window,
     so they expose nothing about 2012 or 2014, and they describe B2's
     own domain. This needs a new protocol version, because B0.1's
     frozen protocol forbids counting zero or positive earnings for any
     year.
6. **Who performs the blinded review that design §3.1 requires for B0,
   and what may that reviewer not open?** Neither this audit's first
   author nor revision 1's author is blind (section 14).
   - Options: (a) an independent review lane with no prior Track B or
     M6-selection reading; (b) the validation-only lane pattern used
     for held-out targets.
   - **Recommended default: (a).** The reviewer is briefed with the
     exclusion list in section 15.4, the inventory's `q6_exclusions`.
     It must log every path it reads, as the U2 M1 builder did
     (`docs/design/u2_m1_runtime_exposure.json`).
     - The list covers 20 files, whole or by line range. It replaces
       the first version's hand list. That list missed all 17
       value-bearing ranges of `m6_projection_engine.md`, §2.7.8 among
       them. It also missed both lock addenda, the candidate-2 program,
       the rest of the candidate-3 program and
       `docs/forecasts/timeline_ledger.json`.
     - The reviewer must not read the 2013 or 2015 family codebooks'
       frequency tables for labor income or its components. Concept
       checks use the variable descriptions only (section 4.2).
     - The reviewer may run the inventory script, which prints no
       content.
7. **Is a count of the population H will start from part of B2's
   registration, or does it move to B0.2 with H?**
   - Facts:
     - B2 scores only the closed 2010 domain at ages 25-64.
     - 950 domain persons under 25 and 1,526 aged 65+ at 2011 are
       projected but never scored at those ages.
     - 982 and 1,672 in-support rows outside the domain at 2012 and
       2014 are not scored at all.
   - **Recommended default: B0.2 with H.** H's starting population is
     one of H's elements, and B2's registration states its closed-domain
     scope.
8. **Does the finding that no unused partition exists fire
   `EXPOSURE_UNRESOLVED` for B2?**
   - Facts:
     - Design line 455 triggers the condition when "B0 cannot establish
       access or an unused partition". It stops "That admission and its
       dependants", and "A registered fallback may proceed only with
       its own narrower scope".
     - Section 5.4 finds no unused partition on B2's target years.
     - B2's dependants are H and B3L (design line 121).
   - Options:
     - (a) B2's retrospective-regression class (design line 150)
       already admits no held-out claim, so the condition does not
       apply to it;
     - (b) the condition fires, and B2's registration is itself the
       registered fallback. Before any candidate outcome, it registers
       with the narrower §3.2 scope ("2010→2014 continuity on the
       stated surface, ages 25–64. Not a 2010-vintage forecast"). It
       states that H and B3L may rely on it only within that scope;
     - (c) the condition fires and blocks B2's admission, H and B3L
       until some other fallback registers.
   - **Recommended default: (b).** It meets the condition's literal
     trigger with the fallback clause the design provides, at the cost
     of one explicit registration statement. (a) reads into line 455
     an exemption its text does not state. (c) would block H and B3L
     although B2 already claims only regression scope.

d622, on B1 v2 unlocking B2, is already queued and is not repeated here.

## 13. Handoffs

- **To the post-ruling B0.1 addendum.** After Max rules on Q1-Q5 and
  Q8, an addendum does four things:
  - freezes elements 5-9 and the planning values;
  - derives the planning values under a new protocol version, if Q5
    chooses (a);
  - recomputes the named power procedure on the ruled basis;
  - goes to its own blinded review.

  B2 registers only on that frozen record (design line 288).
- **To B0.2.**
  - Record B2's result as exposed before J's holdout is chosen (design
    lines 297, 368).
  - The marital selectors' pseudo-boundaries 2008 and 2010 bear on B4.
  - B3L's 2006 boundary coincides with a q\* and ρ\* pseudo-boundary
    whose floor and outcomes are also in the ledgers.
  - Section 11.3's §5.3 figures, if Q4 assigns the limits to B3.
- **To B2.**
  - State collection-wave age and the reference-year versus
    collection-wave mapping (section 4.3).
  - Label the wage vintage separately from `ols_log_nawi_2005_2014`.
  - Reuse the 80-file hash set in `b2_read_set_sha256` as its source
    pin.
  - Record the codebook concept check, definitions only (section 4.2).
  - Carry the §2 candidate-3 disclosure in full.

## 14. Files read and this audit's exposure

Both authors read `RESTRICTED-FILES.md` before opening any evidence
file, and opened no restricted file and no DYNASIM comparator value.

**First version.** It read:

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

**First version's exposure.** `m6_candidate3_program.md:218-228`, read
for this audit, states 2010-boundary objective contributions: the lag-2
autocorrelation term at q = 0.55 and q = 1, and the mobility term at
q = 1. They are standardized squared scores of B2 cells on 2012 and 2014.
This audit's first author is therefore not blind to part of B2's
candidate outcomes. The author also read M6 v4's 2016/2018 floor table,
and a search printed one row of that amendment's candidate-1 seed-score
table (`gate_m6_amendment_1_closed_domain_floors.md:143`). Neither is B2
data. The count run computed no B2 cell, floor or candidate outcome; its
`outcome_blind` block and the unit test pinning its invariance to
earnings values record that.

**Revision 1.** Its author read:

- the blinded review's findings;
- design lines 25-60, 115-155, 275-340 and 435-470;
- this audit, the count script's power and ledger-reading code, the
  count record's power block and count fields, and the audit-record
  test;
- `select_m6_qstar_train_only.py:640-650` and `:1400-1480`;
- `m6_cells.py:477-600`;
- `family.py:596-620` and `:821-860`;
- `gate_m6_amendment_1_closed_domain_floors.md:56-80`, M6 v4's
  2016/2018 floor table, which is not B2 data.

It read key names only in:

- both ledgers' top levels, 2008 boundary blocks and rung blocks
  (q = 0.55, ρ = −0.60), with their objective and F1-analog structure;
- the F1 artifact;
- the selection-evidence pointers in `runs/gate_m6_candidate3_v1.json`;
- the candidate-2 conformance artifact's rows;
- two `data/external/psid_codebook_field_evidence` files.

It read structure without content:

- section headings of `m6_projection_engine.md` (lines 1000-1560 and
  4027-4300), `m6_candidate3_program.md` and the amendment-4 lock
  addendum;
- token-shape summaries of those files, `m6_candidate3_lock_addendum.md`,
  the q\* and ρ\* notes, `paper.qmd` and string values in five JSON
  files. These list the matching pattern families and a count of
  decimal numbers per line, with no line content.

It also read the codebook definitions of `ER52237`, `ER52249`,
`ER58038`, `ER58050`, `ER65216` and `ER65244`, with every digit masked
and each entry cut off before its frequency table. The text extracts
were deleted after use.

**Revision 1's exposure.** Revision 1's author read no 2008- or
2010-boundary value, truth moment, objective contribution or per-draw
output, and no prose that states one. The token-shape summaries show
only which lines carry numbers. The author did read M6 v4's 2016/2018
floor table, which is not B2 data. A search for the lag-2 cell's name
also printed two later lines of that amendment: `:143`, a row of M6
candidate 1's 2016/2018 seed-score ranges, and `:165`, the v4 tolerance
list. Neither is B2 data. The author has read the design, this audit
and the exposure structure, so it is not a suitable blinded reviewer
either.

## 15. Revision 1: response to the blinded review

### 15.1 Findings and what changed

| # | Severity | Finding | Change |
|---:|---|---|---|
| 1 | medium | The exposure history left out boundary 2008, which scored realized 2012, the §2.7.8 prose and other restatements. "Only these three artifacts" held for JSON only | Sections 5.1, 5.2 and 5.5 and the Q6 list (section 15.4) now come from a mechanical inventory. The "only" claim is rescoped to JSON artifacts |
| 2 | medium | §11.3 called worst-case and normal-theory bounds necessary conditions, and recommended `WEAK_POWER_OR_VACUITY` on that basis | Section 11.3 restates feasibility as a function of ρ, λ, s and p, adds M6's published σ as a labelled planning illustration, and withdraws the infeasibility claim and the recommendation. The summary, Q4 and Q5 follow |
| 3 | medium | §11.2 and §11.3 used different, unstated scoring bases | Section 11 names the gap convention and basis for every figure. Q2 gives the full range |
| 4 | medium | Element 5 was marked frozen, several elements were unfrozen, and "freezes" overstated the record | Section 2 marks the record a partial freeze and element 5 open. Section 13 plans a post-ruling addendum with its own blinded review. The PR body is corrected |
| 5 | medium | `EXPOSURE_UNRESOLVED` was not addressed | Section 5.4 and Q8 |
| 6 | low | No codebook concept check; frequency tables are an exposure risk | Section 4.2 and Q6 |
| 7 | low | The count of persons in clusters was understated | Section 10, stated under the one-spouse-per-family condition the frozen record cannot verify |
| 8 | low | The reference variance was unnamed, and post-run figures were unpinned | Section 11.2 names both references, and the audit-record test pins every revision-1 figure |
| 9 | low | The deviation from protocol input 6 was undisclosed, and one citation was off by one | Section 15.2; the citation was changed to `:646`, which round 2 found wrong; revision 2 restores `select_m6_qstar_train_only.py:645` (N4) |

### 15.2 Protocol deviation, recorded 2026-09-29

Protocol input 6 says no ledger field beyond the listed count fields is
read. The count script honoured it: `_ledger_support_counts` reads only
those fields (`scripts/track_b_b0_1_counts.py:812-836`). The written
audit did not. The first version read key names, metadata strings and
provenance fields of both ledgers and of the F1 artifact, for example
`reducer.removed`. Revision 1 read the key names of both ledgers' 2008
boundary blocks and rung blocks, the rung labels, and the F1 artifact's
key names. No value field was read. This is recorded as a deviation of the written audit from the
frozen protocol. The protocol block itself stays byte-identical.

### 15.3 What revision 1 added

- `scripts/track_b_b0_1_exposure_inventory.py` and its one output,
  `docs/design/track_b_b0_1_exposure_inventory.json` (section 5.5).
- `scripts/track_b_b0_1_review_power.py` (section 11). It reads only the
  frozen record's sample sizes and M6 v4's published lag-2 floor σ.
- `tests/test_track_b_b0_1_revision1_tools.py`: invented-data and
  property tests for both scripts.
- New pins in `tests/test_track_b_b0_1_audit_record.py` for the
  inventory's provenance and findings and for every revision-1 figure.

### 15.4 The Q6 exclusion list

These are the inventory's `q6_exclusions`, at `de08c69`. A file with 500
or fewer lines, a JSON file or a figure is excluded whole. Otherwise
the listed line ranges are.

| File | Exclude |
|---|---|
| `docs/amendments/m6_amendment_4_qstar_lock_addendum.md` | whole file |
| `docs/analysis/m6_c3_f1_mechanism_diagnostic_results.json` | whole file |
| `docs/analysis/m6_candidate2_registered_abort_execution_v1.txt` | whole file |
| `docs/analysis/m6_qstar_train_only_selection.md` | whole file |
| `docs/analysis/m6_qstar_train_only_selection_results.json` | whole file |
| `docs/analysis/m6_rhostar_train_only_selection.md` | whole file |
| `docs/analysis/m6_rhostar_train_only_selection_results.json` | whole file |
| `docs/design/m6_candidate2_program.md` | lines 431-452, 607-628, 661-692, 700-711, 855-876, 943-954, 957-980, 1003-1024 |
| `docs/design/m6_candidate3_lock_addendum.md` | whole file |
| `docs/design/m6_candidate3_program.md` | whole file |
| `docs/design/m6_projection_engine.md` | lines 929-943, 1071-1090, 1168-1185, 1192-1216, 1261-1295, 1302-1327, 1338-1349, 1362-1378, 1396-1406, 1410-1421, 1424-1434, 1441-1476, 1487-1504, 1507-1526, 3485-3496, 4076-4100, 4108-4118 |
| `docs/forecasts/timeline_ledger.json` | whole file |
| `gates.yaml` | lines 5775-5785, 5888-5896 |
| `paper/figures/m6_q_frontier.svg` | whole file |
| `paper/paper.qmd` | lines 2233-2253 |
| `tests/test_m6_c3_f1_mechanism_diagnostic.py` | whole file |
| `tests/test_m6_candidate2_runner.py` | lines 160-170, 675-690, 722-740 |
| `tests/test_m6_candidate3_runner.py` | lines 144-154, 662-699, 733-772 |
| `tests/test_m6_qstar_selection.py` | lines 110-120, 742-752, 822-832, 838-848 |
| `tests/test_m6_rhostar_selection.py` | lines 119-138, 205-215, 439-449 |

Line ranges refer to the files at `de08c69`. If a listed file changes
before the review, rerun the inventory to a new path.

### 15.5 Revision 2: round-2 low findings and the d693 correction

| # | Round-2 finding | Change in this file |
|---|---|---|
| N1 | The summary treated a lower bound as a conclusion | Section 1 qualified the side-A figure by its standard error, now called the reference standard error (see the addendum-run row); the pinned strings follow |
| N2 | Floor-equality claims hold only under a person split | Sections 5.4 and 9.2 are conditional on the split; the addendum keeps the person-split floor as a non-gating check |
| N3 | Q2 omitted its main cost | Q2 states the 1.4 times wider tolerance |
| N4 | The corrected citation was off by one the other way | `:645` restored in section 4.3 and in the table above |
| N5 | Exclusion gaps; tracked-files-only scope | Section 5.5 states the scope; the addendum's review root leaves the 20 files out whole |
| N6 | "Pins every one" overstated; mixed-cohort bands; Q4 understated | The audit-record test now pins the prose-only figures; section 11.3 and Q4 are corrected |
| N7 | Wage-vintage element unstated | Section 2 |
| d693 | Q2's 41% is per cell | Q2 and section 11.2 carry the gate-level figures; the addendum recomputes power |
| Addendum review | Section 10 left out M6's all-seeds-valid condition; sections 1-2 still called d622 and the rulings pending | Section 10 restores the condition; the header and section 2 point to the rulings and the addendum's table |
| Addendum run | The planning-value run measured the full-support ratio r above 1 for seven cells | Sections 1, 11 (including 11.2 and 11.4) and Q2 call the standard errors reference points, not bounds |

These changes come after the second blinded review and before the
addendum's own blinded review (Q6), which covers them.

## 16. Protocol record

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
