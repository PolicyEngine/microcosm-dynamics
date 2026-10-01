# Track B B0.1 addendum: the frozen record B2 registers on

**Status: protocol frozen, 2026-10-01; no planning value computed yet.**
This file is the post-ruling addendum that the B0.1 audit
(`docs/design/track_b_b0_1_audit.md`, section 13) calls for. It does
three things:

- it freezes elements 5-9 of design §5.2 for B2, and with the audit's
  frozen elements makes the complete record B2 registers on;
- it derives B2's planning values under a new protocol version, frozen
  in section 16 before any computation;
- it recomputes the named power procedure on the basis Max ruled.

At the commit that adds this file, sections 1-9 and 12-16 are complete.
They hold every rule that decides B2's surface, its pass rule and this
addendum's verdict. Sections 10, 11 and 15 are written after the
planning-value run and the blinded review, and may not change any rule
in the other sections. The protocol block in section 16 never changes.

Verification class: **source audit** (design §3.2). It admits nothing
scientific. "The design" means
`microcosm-launch-evidence/dynasim-parity-20260909/trackb-design-20260928.md`
(revision 3, SHA-256 prefix `6fd6f4aa5a83da80`), outside this
repository; design line numbers refer to it.

## 1. Summary

- **Rulings.** Max ruled on all eight of the audit's questions in d693
  and on the B1 dependency in d622, both on 2026-09-30 (section 2).
- **Record.** All ten §5.2 elements and the power procedure are now
  frozen for B2 (section 3). Elements 6 and 7 freeze rules; B2's floor
  builder produces their values after registration and before any
  candidate run.
- **Scoring rule.** B2 passes only if every gated cell's simultaneous
  95% bound lies within its floor-derived tolerance on full support, and
  M6's seed conjunction holds as well (section 8).
- **Correction.** The audit's 41% room for estimation error at six cells
  is room for one cell. For the whole gate it is 2.8% (section 12).
- **Planning values.** Section 16's protocol derives them from a 2006
  pseudo-origin. One departure from d693's wording needs Max's
  ratification: the refit arm resamples household half-samples without
  replacement, not a bootstrap, because copied households defeat the
  sign gate's early stopping (sections 10 and 13).
- **Results.** Sections 10 and 11 are written after the run.

## 2. Rulings this addendum implements

**d693 (Max, 2026-09-30).** "Yes: accept all eight B0.1 defaults with
the riders in trackb-reviews-20260929/d693-decision-aid/RECOMMENDATION.md
(Q2 as (d): full-support bound rule at k=3 plus M6 seed conjunction,
gate-level power; Q3 household split + person-split non-gating check;
Q5 two variance-only planning values; Q6 isolated read-only review on a
cleaned root; audit Q2 headroom corrected to gate level)."

The table paraphrases each ruling with its riders and says where this
addendum carries it. The riders' own words are in that memo.

| Q | Ruling and riders | Where |
|---|---|---|
| Q1 | (b): all 16 cells, pruned by M6's ladder on B2's own floor. The ladder is ordered by B2's own floor. Power is computed for the whole gate on the Q2 basis. Bonferroni m is the number of cells still gated. Every pruned cell is scored and published. Each gated cell is labelled by exposure and the headline states the split | Section 5 |
| Q1 sub-question | (i): "floors before outcomes" binds B2's own run. These rulings cite no boundary-2008 or boundary-2010 candidate result. PRs #255 and #273, which published those results, merged under Max's account | Sections 5, 14 |
| Q2 | (d): the §5.2 bound rule on full-support scoring at k = 3, with a household-clustered resampled gap standard error and a registered estimation-variance bound, plus M6's seed conjunction as a second condition. Power is computed for the whole gate. The seed conjunction almost never binds when the bound rule passes. Cost: the tolerance is about 1.4 times wider in standard-error units than under M6's side-A scoring. If the estimation-variance bound leaves no room for four cells, B2 is `WEAK_POWER_OR_VACUITY` and is rescoped before any candidate outcome | Sections 7, 8, 11, 16 |
| Q3 | Household split, with the person-split floor as a non-gating reproduction check | Sections 4, 9 |
| Q4 | (a): §5.3's limits do not apply to B2. Each gated cell's tolerance is stated in plain units before any outcome. One scope sentence: no Track B gate holds ages 25-61 earnings to a fixed limit. §5.3 feasibility is reviewed once, at B0.2, for B3 and B3L | Sections 6, 13 |
| Q5 | (a): B2's own window through 2010 under a new, frozen, outcome-blind protocol, with two variance-only values per cell (estimation variance; shared-anchor ratio) from one pseudo-origin household bootstrap, and no levels or gaps. M6's published floor is used only as a labelled illustration | Sections 10, 16 |
| Q6 | (a), hardened: an independent Opus lane in Subfleet's isolated-review mode on a cleaned root, with no shell and no web. The root leaves out the 20 §15.4 files whole, the PR threads of #255, #271 and #273, the #42 registration comments and the launch-evidence directory. Numerical reproduction goes to CI-pinned tests. A review that touches a denied path does not count | Section 15 |
| Q7 | B0.2 with H. H's spec names and counts its 2010 start roster, and B4's coverage declaration cites it. B2's bridge hands its frozen 13,542-person domain to H, and B2 scores no one outside ages 25-64 at the scored waves | Sections 4, 13 |
| Q8 | (b): `EXPOSURE_UNRESOLVED` fires, and B2's registration is the registered fallback at its §3.2 scope, stated before any candidate outcome. Removing the statement after candidate runs needs a dated amendment | Section 4 |

**d622 (Max, 2026-09-30).** "Yes: a B1 v2 reconstructed-reproduction
pass may unlock B2 (and H), with the weaker label carried into B2's
registration." Section 13 carries it.

**The Q2 correction** and the round-2 review's low findings N1-N7 are in
section 12.

## 3. The frozen record

Design line 288: "Each record lists all ten elements above, plus the
named power procedure. A gate cannot register until its record is
frozen." This table is B2's record. It supersedes the audit's section 2
table.

| Element | Status | Where |
|---|---|---|
| 1. Source release | Frozen | Audit §4.1 and §4.3; the wage vintage is the policyengine-us 1.752.2 NAWI realized through 2010, with the fitter's log-linear projection over 2001-2010 after it (audit §2, N7) |
| 2. Variables | Frozen | Audit §4.2 |
| 3. Population | Frozen | Audit §7: the 13,542-person 2010 domain, handed to H by B2's bridge; no one is scored outside ages 25-64 at the scored waves (Q7) |
| 4. Exposure history | Frozen | Audit §5 and its inventory; the exposure labels (section 5) and the Q8(b) fallback (section 4) settle its consequences |
| 5. Holdout partition | Frozen | Section 4 |
| 6. Critical cells | Rule frozen | Section 5 |
| 7. Numerical tolerances | Rule frozen | Section 6 |
| 8. Uncertainty treatment | Frozen | Section 7 |
| 9. Pass conjunction | Frozen | Section 8 |
| 10. Reference dates vs availability | Frozen | Audit §4.3 |
| Named power procedure | Frozen | Section 16 (protocol v2), evaluated in sections 9 and 11 |

"Rule frozen" means the derivation rule is fixed here. Its values need
B2's floor, which B2's pinned floor builder computes after registration
and before any candidate run, as M6's did (design line 332).

## 4. Element 5: holdout partition

- **Estimation.** Earnings rows with reference year 2010 or earlier
  (`forward_earnings.py:1021-1024`), fitted at ages 25-64, with anchors
  of any age. The wage vintage is element 1's.
- **Evaluation.** Realized 2012 and 2014 rows on the frozen 2010 domain,
  at collection-wave ages 25-64.
- **Split unit.** The 2011 household, identified by the 2011 interview
  number, for floor seeds 0-99 and gate seeds 0-4. Each seed splits the
  full 2011 anchor first
  (`split_panel_by_person(persons, "household_id", fraction=0.5, seed)`,
  as `m6_scoring.side_a_person_ids` does for household-split families)
  and then intersects each half with the domain.
- **No unused partition.** Every evaluation row lies in years the audit
  lists as exposed (audit §5). Under Q8(b), `EXPOSURE_UNRESOLVED` fires
  and B2's registration is the registered fallback. The registration
  states, before any candidate outcome:
  - its scope is §3.2's: "2010→2014 continuity on the stated surface,
    ages 25–64. Not a 2010-vintage forecast" (design line 150);
  - H and B3L may rely on B2 only within that scope;
  - removing this statement after any candidate run requires a dated
    amendment.
- **Person-split reproduction check (non-gating).** Section 9 defines
  it. It gates nothing.

## 5. Element 6: critical cells

**Candidate family.** The 16 gateable cells of audit §9.1.

**Eligibility.** A cell can gate only if both hold:

- on B2's household-split floor, all 100 seeds are defined and the
  weaker half holds at least 20 events on every seed (`m6_cells.py:56`);
- it has planning values in this addendum's record (section 16, step 9).

**Pruning.** M6's decompounding ladder (`gates.yaml:5590-5599`;
`scripts/build_m6_holdout_floors_v2.py:330-373`), run on B2's own floor:

1. order the eligible cells by descending tolerance/σ on B2's
   household-split floor, ties by cell name;
2. compute the gate-level power of the cells still gated, by the named
   procedure on its binding evaluation, with Bonferroni m equal to the
   number of cells still gated;
3. if the power is at least 0.90, stop;
4. otherwise take the next cell in the order. If it is the last eligible
   cell of its concept family, keep it and move on. If not, prune it and
   return to step 2.

The concept families are M6's: log quantiles (p10, p50, p90), zero
rate, dispersion (Δlog SD), change mean (Δlog mean), mobility and
autocorrelation.

**Guards.** At least four gated cells, and not every gated tolerance at
its cap (`m6_cells.py:64-67`). In M6 the four-cell guard counted flow
cells; here it counts B2's earnings cells. With six eligible families
the ladder cannot go below six cells, so the four-cell guard binds only
if three or more families have no eligible cell.

**If the ladder ends below 0.90 or a guard fails.** B2 is
`WEAK_POWER_OR_VACUITY` (design line 454). The floor artifact records
it, B2 stops, and a decision is queued for Max with the rescoping
options. No rescoped registration is written before he rules. This
covers every case d693's Q2 flip names.

**Pruned cells.** Every pruned or ineligible cell is scored and
published, report-only, with its own unadjusted 95% interval, outside
the Bonferroni family.

**Exposure labels.** Each gated cell carries one of two labels, and the
headline states how many gated cells carry each:

- "published candidate-3-law outcomes at boundaries 2008 and 2010": the
  six M6-retained cells (`earn_p10.prime`, `earn_dlog_mean.prime`,
  `earn_dlog_sd.older`, `earn_mob_h1_diag`, `earn_autocorr_lag2`,
  `earn_zero_rate.older`);
- "published five-seed floor detail, no published candidate outcome":
  the other ten.

The pruning rule never refers to exposure. "Floors derived before
candidate outcomes" (design line 332) binds B2's own registered run:
the floor builder is pinned and its artifact committed before B2's
candidate runs, and the public selector floors are recorded as prior
exposure.

## 6. Element 7: numerical tolerances

- **Rule.** tol_c = min(round(mean_c + 3 × SD_c, 3), cap), from the 100
  household-split floor seeds of B2's truth-only floor
  (`m6_cells.py:48`, `:691-698`). The caps are ln 1.5 for `log_ratio`
  and `abs_gap_log` cells and 0.15 for `abs_gap_corr` cells
  (`m6_cells.py:746-752`). No 2016/2018 tolerance is transplanted.
- **§5.3.** Its earnings limits do not apply to B2 (Q4). No Track B gate
  holds ages 25-61 earnings to a fixed limit; B2's registration carries
  that sentence.
- **Plain units.** Before any candidate outcome, the floor artifact
  states each gated tolerance in plain units:
  - `log_ratio` t: "within a factor of e^t", with the percentage;
  - `abs_gap_log` t: "mean two-year log change within ±t";
  - `abs_gap_corr` t: "correlation within ±t".

## 7. Element 8: uncertainty treatment

For each gated cell c, on full support:

- **Upper-bound standard error.** se_up,c = SD of the truth statistic's
  deviation over 4,000 household-bootstrap replicates × √(1 + 1/K). It
  is truth-only, and the floor builder computes it before any candidate
  outcome.
- **Bootstrap standard error.** se_boot,c = SD of the signed gap over
  4,000 household-bootstrap replicates, with the law fixed and each
  person's projected paths fixed.
- **The bootstrap.** Both use the same replicates: multinomial
  multiplicities over all 2011 full-anchor households (equal
  probabilities, as many draws as households, a registered seed),
  households without a domain person included. Each person in a
  household with multiplicity c is copied c times under new identifiers,
  truth rows and every draw's projected rows alike, by this addendum's
  `copy_persons`. Weights are never multiplied instead, because the
  mobility cells bin by midpoint weighted ranks.
- **Registered standard error.** se_c = √(se_boot,c² + a_c × se_up,c²),
  where a_c is the cell's registered estimation-variance ratio from
  section 10: e_B2,c, plus the transported cross term where section 16's
  rule adds it. a_c is never negative, so se_c is at least se_boot,c.
- **Bound.** |g_c| + z\*_m × se_c, with z\*_m the two-sided simultaneous
  95% value over the m gated cells, Φ⁻¹(1 - 0.05/(2m)).
- **Monte Carlo error.** The SD over the K = 20 draws of the per-draw
  signed gap (ln(P_k/T) for `log_ratio` cells, P_k - T otherwise),
  divided by √K, must be below tol_c/10 (design line 302). A cell that
  fails cannot pass. Side-A seeds carry no Monte Carlo rule, as in M6.
- **Undefined replicates.** A gated cell with more than 1% of its
  bootstrap replicates undefined cannot pass.
- **Survey design.** The household bootstrap is the resampling d693
  ruled (Q2, Q3). It does not resample PSID's sampling-error strata and
  clusters. Section 16 measures what that leaves out at the
  pseudo-origin (the design ratio) and fixes the rule that follows from
  it.
- **Side A.** Each gate seed's side-A statistics come from the
  full-domain projection's K draws, restricted to side-A persons. B2
  does not re-project each half.

## 8. Element 9: pass conjunction

A gated cell is **valid** on a frame when none of its K draws is
undefined and the K draw values are not all identical. That is M6's
rule (`m6_scoring.py:713-733`).

The outcome is the first of these that applies:

1. **INVALID** if any gated cell is not valid on full support or on any
   of the five gate seeds' side A. M6 requires all five seeds valid
   (`m6_scoring.py:744-750`).
2. **FAIL** if either holds:
   - fewer than four of the five gate seeds pass, a seed passing when
     every gated cell's side-A gap is within tol_c;
   - some gated cell's full-support gap is outside tolerance,
     |g_c| > tol_c.
3. **PASS** if, for every gated cell, all hold:
   - the bound lies within tolerance, |g_c| + z\*_m × se_c <= tol_c;
   - se_c and the Monte Carlo error are defined, the Monte Carlo rule
     holds, and at most 1% of its bootstrap replicates are undefined.
4. **INCONCLUSIVE** otherwise: the point gaps are within tolerance but
   the precision does not show it.

Notes:

- §5.2 says "Insufficient precision is inconclusive, never a pass"
  (design line 304). Calling a point gap outside tolerance FAIL, not
  INCONCLUSIVE, is this addendum's choice, made for continuity with M6,
  which scores the point gap.
- INVALID and INCONCLUSIVE are non-passes with FAIL's consequences.
  Each blocks B2's admission and its dependants, H and B3L (design line
  445). Each is published with every gated and pruned cell scored, and
  each counts as an attempt in the cumulative ledger (design line 469).
- After any candidate outcome this registration permits no rerun, no new
  draw or bootstrap seed, no larger K, and no re-pruning, tolerance
  change or rescoping. `WEAK_POWER_OR_VACUITY`'s rescoping route applies
  only at floor build, before candidate outcomes.

## 9. What B2's floor builder and comparator do

This replaces the audit's draft rule (§9.2) on the ruled basis.

1. B2's registration on #42 pins the floor builder's commit, the
   comparator's commit and this addendum before either runs.
2. The builder is truth-only. It defines the domain from data alone
   (2011 anchor persons with a valid 2010 row) and reads no candidate
   output, projection or selection ledger. It does read this addendum's
   planning-value record, which holds only variance ratios from the 2006
   pseudo-origin, and it says so in its artifact.
3. It computes the household-split floor (section 4's split, seeds
   0-99) and, without gating on it, the person-split floor.
4. It computes each cell's tolerance (section 6) and se_up,c (section 7).
5. It applies eligibility, the ladder and the guards (section 5), with
   power from the named procedure on its binding evaluation: r_c and
   s²_gate,c from section 10, and τ_c = tol_c / se_up,c.
6. It publishes the floor artifact and its hash: the gated cells with
   exposure labels and plain-unit tolerances, the pruned cells, the
   power, and the canonical SHA-256 of its person-split floor block and
   seed 0-4 detail for the six M6-retained cells. B2's candidate runs
   only after this artifact is committed.

**The comparator** is a separate script, not the builder. After the
floor artifact is committed, it reads two fields of each boundary-2010
selection ledger and nothing else: the six cells' person-split floor
block and the seed 0-4 floor detail. It prints only whether their
canonical SHA-256s equal the builder's. A mismatch is published and
gates nothing. The ledgers are on the Q6 exclusion list, so the
comparator's run is recorded as a ledger read.

## 10. Planning values

*Written after the run.*

## 11. Power on the ruled basis and the verdict

*Written after the run.* The figures that need no planning value are
already fixed. On the audit's upper-bound basis (r = 1, no estimation
error), at uncapped k = 3 tolerances:

| Gated cells | Bound rule alone | Bound rule and seeds | Room for estimation error | Bound rule × M6's own seed convention |
|---:|---:|---:|---:|---:|
| 1 | 0.998 | 0.998 | 99% | 0.997 |
| 4 | 0.962 | 0.962 | 16.0% | 0.950 |
| 5 | 0.941 | 0.941 | 8.4% | 0.924 |
| 6 | 0.917 | 0.917 | 2.8% | 0.893 |
| 16 | 0.584 | 0.584 | none | 0.502 |

"Room" is the largest estimation variance, as a share of the
survey-plus-simulation gap variance, at which the bound rule still
passes a faithful candidate with probability 0.90. On this model the
seed conjunction fails, given a bound-rule pass, with probability below
0.001 at every size.

## 12. Corrections to the audit

**Q2's headroom is per cell.** The audit's Q2 facts said the
full-support bound rule leaves "41% of the gap variance at m = 6" for
estimation error. `bound_rule_pass_probability`
(`scripts/track_b_b0_1_counts.py:539-545`) is the probability that one
faithful cell passes, and design line 300 requires every gated cell to
pass. With cells treated as independent:

- per cell, the room is 41.1% at m = 6, which is the audit's figure;
- for the whole gate it is 2.8% at six cells, 8.4% at five and 16.0% at
  four, each at its own z\*, and there is none at 16;
- before estimation error the bound rule passes all six cells with
  probability 0.917, and all 16 with 0.584.

The d693 memo gave 0.919 and about 3.2% at six cells, and about 6% and
10% at five and four with z\* held at its six-cell value. The figures
above replace them.

**Round-2 low findings.**

| # | Disposition |
|---|---|
| N1 | Audit §1 now says "at the upper-bound standard error"; the pinned string follows |
| N2 | Audit §5.4 and §9.2 make the floor-equality claims conditional on a person split. Under the ruled household split the gating floor is new, and the person-split floor is a non-gating check run by the comparator (section 9) |
| N3 | Audit Q2 states the cost: the tolerance is about 5.1 standard errors wide on full support against about 3.6 on side A, about 1.4 times wider |
| N4 | `select_m6_qstar_train_only.py:645` restored in audit §4.3 and §15.1 |
| N5 | Audit §5.5 states that the inventory covers tracked files only. The review root leaves every listed file out whole, and section 15 adds the paths the inventory cannot see |
| N6 | The audit-record test now pins the prose-only figures; audit §11.3 and Q4 give the bands by cohort and add the side-A Kish band |
| N7 | Audit §2 says element 1 freezes the wage vintage and why |

The review of this addendum's own draft found two more points in the
audit, both fixed there: §10 left out M6's requirement that all five
seeds be valid, and §11.2's per-cell room figures were unlabelled.

## 13. Preconditions, open decisions and handoffs

**B2 may register only when all of these hold:**

- this addendum is merged with its planning values, and its Q6 review
  counted (section 15);
- section 11's verdict is "feasible", or Max has ruled on the decision
  that a different verdict queues;
- Max has ratified the refit arm's half-sample resampling, or ruled
  otherwise (below);
- a B1 run has passed: v1 `REPRODUCED`, or v2
  `RECONSTRUCTED_REPRODUCTION` (d622). A v2 pass carries its weaker
  label, "reconstructed reproduction (weaker than bit-for-bit)", into
  B2's registration and every downstream disclosure. A
  `BASELINE_REPLAY_MISMATCH` stops B2 (design line 451). No B1 run
  artifact is committed as of this addendum.

**Decision queued for Max.** d693's Q5 rider says the two planning
values come from "one pseudo-origin household bootstrap". Arm F is a
household bootstrap. Arm R, which refits the law, resamples household
half-samples without replacement, for the reason and evidence in section
16, step 6. The alternative is a new protocol version with a
with-replacement refit arm.

**To B2.**

- State collection-wave age and the reference-year versus
  collection-wave mapping (audit §4.3).
- Label the wage vintage separately from `ols_log_nawi_2005_2014`.
- Reuse the 80-file hash set in `b2_read_set_sha256` as the source pin.
- Record the codebook concept check, definitions only (audit §4.2).
- Carry the §2 candidate-3 disclosure in full.
- State that the planning values come from a window whose truth years,
  2008 and 2010, fall in a recession, and that neither their transport
  to 2012 and 2014 nor r's is tested.
- Import `copy_persons` and the multiplicity functions from
  `scripts/track_b_b0_1_planning_values.py` for the scoring bootstrap,
  and test that the scorer and arm F build identical frames for the
  same multiplicities.

**To B0.2.**

- Record B2's result as exposed before J's holdout is chosen (design
  lines 297, 368).
- The marital selectors' pseudo-boundaries 2008 and 2010 bear on B4.
- B3L's 2006 boundary is a q\* and ρ\* pseudo-boundary whose floor and
  outcomes are in the ledgers. Protocol v2 also projects candidate 3's
  law from 2006 to 2008 and 2010 at ages 25-64, which includes B3L's
  62-64 band, and publishes variance ratios there.
- §5.3 feasibility is reviewed once, for B3 and B3L, with audit §11.3's
  figures as inputs.
- H's spec names and counts its 2010 start roster, and B4's coverage
  declaration cites it.
- If section 16's design rule does not hold, the same question arises
  for every later gate's resampling.

## 14. Reads and exposure

**Author.** The orchestrating Claude Code session (Opus 5.5) that wrote
this addendum also designed protocol v2: the pseudo-origin, the arms,
the transport rule, the binding evaluation and the verdict rule. It is
not the author of the audit or of its revision 1, and it shares no
context with them. Before the freeze it read:

- `RESTRICTED-FILES.md` (the list, and no file on it);
- the audit in full; the d693 decision aid's `RECOMMENDATION.md`; the
  round-2 review; PR #490's comments; the d693 and d622 decision
  records;
- design lines 20-160, 275-345 and 435-475;
- the B1 v2 amendment and lines 110-135 of the B1 draft;
- code: `select_m6_qstar_train_only.py` (lines 1-200, 300-700,
  880-1860, 2195-2294), `forward_earnings.py` (1004-1262, 1347-1480 and
  matches for gates and person identifiers), `refit.py`, `candidates.py`,
  `earnings_domain.py`, `m6_cells.py`, `m6_scoring.py` (380-430,
  690-752), `moments.py` (34-248), `panels.py` (183-260),
  `psid2010.py` (903-970), `family.py` (622-640),
  `build_m6_holdout_floors_v2.py` (110-160, 325-400), the three B0.1
  scripts and `tests/test_track_b_b0_1_audit_record.py`;
- `gates.yaml` lines 5500-5620, and `m6_projection_engine.md` lines
  3689-3765, which hold M6's 2016/2018 operating characteristic and
  ladder and no boundary value;
- the test doubles in `tests/test_m6_engine_forward_earnings.py` and
  `tests/test_m6_engine_correlated_refresh.py`.

It opened none of the 20 files on the audit's §15.4 list other than
those two line ranges, no selection ledger, no codebook frequency table
and no PSID data before the freeze. It did not read the ledgers' 2006
blocks, so the pseudo-origin, the transport rule and the binding
evaluation were chosen without them. It ran the audit-record tests,
which rescan listed files mechanically and print nothing from them.

One disclosure. On 2026-09-30 at 22:30 UTC, `RESTRICTED-FILES.md` added
the Claude project folder that holds this session's transcripts, because
other sessions in that folder run a validation lane for an unrelated
registration. After that time this session read files in its own
subfolder there: its own oversized tool outputs, and the journal of its
own pre-freeze review agents. It opened no other session's folder. It
is not a builder for that registration.

**Pre-freeze design review.** Four independent reviewers (in-session
Opus 5.5 agents, each with one lens: rulings, power, blindness,
statistics) and their verifiers read the draft protocol and plan under
the same exclusions. Their findings shaped sections 4-9 and 16. None of
them can serve as the Q6 reviewer.

**Method for the final record.** `docs/design/track_b_b0_1_addendum_reads.json`
is extracted mechanically from this session's own transcript export:
every file-reading tool call's path and range, and every shell command,
with no tool output. Section 15 adds the Q6 lane's read log.

## 15. The blinded review (Q6)

*The record is written after the review.* The plan, fixed now:

- **Root.** `git archive` of the PR head into a new directory that is
  not a git repository and is outside every restricted folder. Removed
  whole: the 20 files of audit §15.4; every further file the exposure
  inventory flags when rerun at the PR head; and
  `data/external/psid_codebook_field_evidence/`, whose code maps carry
  frequency columns for B2's 2012 and 2014 labor-income variables. The
  builder then refuses the root if any remaining file holds a code map
  with frequencies for a 2013 or later interview wave.
- **Context copies.** Five named files are copied in, each hashed and
  scanned with the inventory's patterns: the Track B design, the d693
  `RECOMMENDATION.md`, PR #490's two review comments, and the d693 and
  d622 ruling texts. They are the only launch-evidence material in the
  root.
- **Lane.** `subfleet run --task review -m opus -I -s read-only -D
  <root>`: Read, Glob and Grep only.
- **Read log.** Every path in every tool call and tool result of the
  lane's transcript is extracted mechanically. A review that touches a
  path outside the root, or a denied path, does not count, and a new
  one is dispatched.
- **Numbers.** Numerical reproduction is in the CI-pinned tests, not the
  reviewer's job.

## 16. Protocol record

The block below was committed and pushed before any planning value was
computed. Its SHA-256, over the text from the begin marker through the
end marker, is pinned in `scripts/track_b_b0_1_planning_values.py`
(`PROTOCOL_V2_SHA256`) and in
`tests/test_track_b_b0_1_addendum_record.py`. The script refuses to run
unless the block hashes to that value.

<!-- protocol-v2:begin -->
## Planning-value protocol, version 2 (frozen before any computation)

### Why a new version

Max's ruling d693 (2026-09-30) adopted Q5 option (a) with a rider. B2's
planning values come from B2's own estimation window, reference years
2010 and earlier, under a new, frozen, outcome-blind protocol. They are
two variance-only values per cell from one pseudo-origin household
resampling: the estimation variance, and the shared-anchor ratio (the
true gap standard error over its upper bound). No level or gap is
recorded. Version 1, the structural-audit protocol committed at
`e51216f`, forbids counting zero or positive earnings for any year, so it
cannot produce them. This is version 2. Version 1 is unchanged.

### What this protocol may and may not compute

- **Forbidden.** Nothing is read, fitted, projected or computed for
  reference year 2011 or later. The only PSID files opened are the
  cross-year individual file and the family files of collection waves
  1969-2011; a guard refuses any other open before it happens. From the
  individual file, only the fields of collection waves 2011 and earlier
  and the two wave-less sampling-error variables are parsed. NAWI is read
  through its 2006 key and no further. So no B2 gate statistic, candidate
  outcome, floor or cell value on reference years 2012 or 2014 is
  computed, and none can be.
- **Allowed.** At the pseudo-origin 2006 the script fits candidate 3's
  law on rows dated 2006 and earlier, projects it to 2008 and 2010, and
  computes the realized 2008 and 2010 cells. Every row lies in B2's
  estimation window. It also recounts three figures the frozen record
  already holds for B2's own 2010 boundary, and counts B2's anchor
  forward pairs, all from rows dated 2010 or earlier.
- **Recorded.** Per cell: an eligibility flag, replicate counts, and
  ratios to the cell's own upper-bound standard error (r, e, their
  limits, the gap-variance ratio, the design ratio and the diagnostics
  named below). Also: support and pair counts that are not split by
  earnings sign, arm F's correlation matrix of the cells' gaps, hashes,
  seeds and provenance. The record holds no truth moment, projected
  moment, cell level, gap, mean gap or per-replicate value, and no
  raw-scale variance, floor σ or event count: with known sample sizes
  those can imply a level. The script refuses to write any key outside
  its listed set.
- **Transient.** Per-replicate checkpoints sit outside the repository.
  They hold signed gaps, truth deviations and refit effects for reference
  years 2006-2010, and no truth or projected value. Nobody opens them.
  They are deleted when the run completes or fails; an infrastructure
  interruption keeps them for a logged resume.

### Inputs

1. The staged PSID directory, named by `POPULACE_DYNAMICS_PSID_DIR`.
2. From `ind2023er/IND2023ER.txt`: age, sequence, relationship, weight
   and interview number for every family collection wave from 1969
   through 2011 (`panels.ind_person_period` with an explicit wave list),
   and the sampling-error stratum and cluster, `ER31996` and `ER31997`
   (`cohorts.age67.read_design_variables`), which carry no wave.
3. From each of those waves' family files: the interview number and the
   head and spouse labor-income levels, read by the q\* selector's field
   reader (`select_m6_qstar_train_only._read_family_labor_levels`) with
   its label and reference-year checks.
4. The policyengine-us 1.752.2 `nawi.yaml`, read through the selectors'
   prefix reader, stopping at the 2006 key. Its prefix byte count, prefix
   SHA-256 and mapping SHA-256 must equal the selectors' pinned 2006
   values (`select_m6_qstar_train_only.EXPECTED_BOUNDARY_NAWI[2006]`).
5. Code: candidate 3's registered engine law, `CANDIDATE_3`
   (`src/populace_dynamics/engine/candidates.py`), through
   `refit_earnings_chained_generator`; the selectors' projection loop
   (`select_m6_qstar_train_only._project`); the M6 reducer
   `earnings_cells` and floor function `run_floor`
   (`src/populace_dynamics/harness/m6_cells.py`).
6. Runtime: Python 3.14.4, NumPy 2.5.1, pandas 3.0.3, scikit-learn 1.8.0,
   SciPy 1.18.0, quantile-forest 1.4.2, and populace-fit and
   populace-frame 0.1.0 installed editable from populace commit
   `af02c917fcb3c50816bf3af9c2b64509e928889a` with the selectors' pinned
   fit and frame trees. The script refuses any other runtime.
7. From the frozen record `docs/design/track_b_b0_1_counts.json`: B2's
   per-cell support counts at its 2010 boundary.

### Definitions

- **Pseudo-origin.** b = 2006, with anchor wave 2007 and horizons 2008
  and 2010 (collected in 2009 and 2011). Level years are (2008, 2010) and
  change years (2006, 2008, 2010). This is B2's geometry (origin 2010,
  anchor wave 2011, horizons 2012 and 2014) moved back four years, and
  2006 is the latest origin whose horizons end by 2010. It is also one of
  the three pseudo-boundaries whose scored outcomes were summed in the
  q\* and ρ\* selection objectives
  (`select_m6_qstar_train_only.py:114`, `:1832-1850`), so candidate 3's
  law is in-sample on this window, as it is at B2's own origin. The
  selection ledgers' 2006 blocks are not read or compared.
- **Earnings rows.** For each collection wave w, the rows of persons
  present (sequence 1-20) as head or spouse, dated to reference year
  w - 1, kept when the level is below the PSID missing sentinel and the
  wave weight is positive (the selectors' construction).
- **Full anchor.** Persons with sequence 1-20 and positive weight at the
  2007 wave. Fixed weight: their 2007 weight. Household: their 2007
  interview number.
- **Fit.** `refit_earnings_chained_generator(rows dated <= 2006, NAWI <=
  2006, seed=5200, boundary_year=2006, candidate_spec=CANDIDATE_3)`.
- **Domain.** Full-anchor persons in the fitted earnings domain (a valid
  2006 row). The script asserts, as the selectors do, that this set
  equals the fitted anchor set.
- **Truth support.** Domain persons' earnings rows at 2006, 2008 and 2010
  whose collection-wave age is 25-64, with the fixed weight and the M6
  cohorts (prime 25-44, older 45-64).
- **Projection.** For each draw seed 6200-6219 (K = 20), the selectors'
  `_project` on the domain, restricted to the truth support.
- **Cells.** The 16 gateable cells of `earnings_cells(level_years=(2008,
  2010), change_years=(2006, 2008, 2010))`: every cell whose metric is
  `log_ratio`, `abs_gap_log` or `abs_gap_corr`.
- **Signed gap.** For a cell and a frame, the projected statistic P̄ is
  the mean over the K draws of the draw's cell value, and T is the truth
  value on the same persons and weights. The gap is ln(P̄/T) for
  `log_ratio` cells and P̄ - T otherwise: M6's score before the absolute
  value (`select_m6_qstar_train_only._score`). It is undefined where M6
  leaves the score undefined.
- **Truth deviation.** A replicate's truth value against the full
  sample's, in the gap's scale: ln(T_b/T) or T_b - T.
- **Copying.** A person with multiplicity c is copied c times under new
  identifiers (person id × 1000 + copy), truth rows and each draw's
  projected rows alike, so copies share the person's projected paths.
  Weights are never multiplied instead: the mobility cells bin by
  midpoint weighted ranks (`moments._weighted_quantile_bin`), so the two
  are not equal.

### Computations

1. **Source reproduction.** From the rows read, recount B2's 2010
   boundary: 321,500 fit-input rows, 23,134 full-anchor persons and
   13,542 domain persons. Any difference from the frozen record aborts
   the run.
2. **Full-sample fit, projection and forest check.** Fit the law, build
   the domain and truth support, and project the K draws. Then refit the
   full sample with RegimeGatedQRF's per-sign quantile forests skipped.
   The forward law draws signs from each gate's classifier and levels
   from donor pools, and never reads those forests
   (`forward_earnings.py:1161-1179`, `:1780-1800`). The skipped refit
   must reproduce both gates' classifier state and probability surface,
   and the projections of draw seeds 6200 and 6201, byte for byte, or
   the run aborts. Arm R's refits skip the forests.
3. **Household-split floor.** `run_floor` on 2007 households (the Q3(b)
   split), floor seeds 0-99, truth only. It is used for two things: each
   cell's eligibility (all 100 seeds defined, at least 20 weaker-half
   events on every seed, the M6 rule), and one units check.
4. **Arm F: fixed law, household bootstrap, 4,000 replicates.**
   Replicate b draws household multiplicities from a multinomial over
   all H full-anchor households (equal probabilities, H draws) and copies
   persons. From the one full-sample projection it recomputes T and the
   K draw values on the copied frames, and keeps the signed gap and the
   truth deviation.
5. **Arm D: the same with design clusters, 1,000 replicates.** Instead
   of households, PSID sampling-error clusters are resampled within
   strata (Rao-Wu): in a stratum with two clusters one is drawn and
   copied twice; a stratum with one cluster keeps it once; a stratum
   with three or more draws that many with replacement and is counted.
   It keeps the signed gap.
6. **Arm R: refit, household half-samples, 60 to 200 replicates.**
   Replicate b keeps a random half of the full-anchor households and a
   random half of every other cluster, without replacement. A person
   outside the full anchor with a row dated 2006 or earlier belongs to
   the household (collection wave, interview number) of their last
   present wave at or before 2007. The law is refitted on the kept
   persons' rows (same seed, NAWI and candidate), the domain and support
   are rebuilt, and the K draws are projected. On the same kept frame
   the fixed-law statistic comes from the full-sample projection's
   paths. For each cell the replicate keeps:
   - δ: the refit-law projected statistic minus the fixed-law one
     (ln of their ratio for `log_ratio` cells);
   - w: the simulation variance of δ, the draw-to-draw variance of the K
     paired differences over K (after dividing each law's draws by its
     own mean for `log_ratio` cells);
   - the same for the simulation covariance of δ with the fixed-law
     statistic, and both laws' signed gaps.

   A half-sample statistic's deviation from the full-sample one has the
   full sample's variance, so Var(δ) estimates the variance of the law's
   estimation effect with no rescaling. Half-samples replace
   with-replacement copies here because copies defeat the sign gate's
   early stopping: its 10% validation split is drawn by row, so a copied
   person's rows fall on both sides. On an invented panel (37,552 pairs,
   24 refits per scheme) the full fit stopped at 23 boosting iterations,
   half-sample refits at 11-30, and every copied refit ran to the cap of
   100, with about three times the prediction variance. d693 says
   "bootstrap"; arm F is one, arm R is not, and that difference is
   disclosed to Max.
7. **Per-cell values.** With se_up = SD(truth deviation over arm F) ×
   √(1 + 1/K), the audit's upper bound with the truth statistic's
   standard error taken from the replicates:
   - shared-anchor ratio r = SD(gap over arm F) / se_up;
   - estimation variance e = (Var(δ) - mean(w)) / se_up² over arm R;
   - gap variance s² = r² + f × max(0, e), with f the transport factor
     (step 8);
   - limits: replicate indices are resampled 2,000 times, arm F's gap
     and truth deviation together and arm R's values together. The
     record holds the 5th and 95th percentiles of r and e, and upper
     limits at the 97.5th percentile, e_ucl and s²_ucl, because
     percentile limits from this many refits under-cover a one-sided 95%
     bound;
   - cross term c = 2 × (Cov(fixed-law gap, δ) - mean simulation
     covariance) / se_up² over arm R, with its 5th and 95th percentiles.
     e leaves out this covariance between estimation and sampling error.
     If the 5th percentile is above zero, the cell's gating variance
     adds f × c; otherwise c is a diagnostic;
   - s²_gate = s²_ucl, plus f × c under that rule;
   - design ratio d = SD(gap over arm D) / SD(gap over arm F), with its
     5th and 95th percentiles;
   - diagnostics: the simulation share of Var(δ); Var(refit-law gap) -
     Var(fixed-law gap) over se_up²; the floor's σ over twice the truth
     deviation's SD (near 1 if the floor and the bootstrap agree); and
     the full-sample projected statistic's draw-to-draw SD over √K, over
     se_up.
8. **Transport to B2.** For cell c, f_c = max(1, (n_B2,c / n_2006,c) ×
   (P_2006 / P_2010)). n is the cell's scored support (level rows by
   cohort, two-year pairs by cohort, pooled two-year pairs, or four-year
   pairs, as the frozen count script defines them) and P the anchor
   forward-pair count the law's gates and pools are fitted on. B2's
   registered estimation-variance ratio is e_B2,c = max(0, e_ucl,c) ×
   f_c. r transports unchanged. Neither transport is tested here: the
   2008 and 2010 truth years fall in a recession, and B2's registration
   says so.
9. **Cells without planning values.** A cell has planning values only if
   its floor is eligible, no arm is void, at least 99% of arm F's
   replicates are defined, and every arm R replicate that completed is
   defined.
   Otherwise it is recorded as undefined with the reason, and it cannot
   gate B2.
10. **The design rule.** If every defined cell's design-ratio 95th
    percentile is at most 1.10, household resampling (d693's Q2 and Q3)
    stands for B2. Otherwise the choice between inflating B2's standard
    error and resampling design clusters goes to Max before any
    candidate run.

### Named power procedure on the ruled basis (no data enter)

Units are each cell's se_up. For cell c with shared-anchor ratio r_c,
gap variance v_c, registered variance v_reg,c and tolerance τ_c:

- the full-support gap is x ~ N(0, v_c);
- given x, each gate seed's side-A gap is independently N(x, r_c²). A
  random half of the households has twice the full sample's sampling
  variance, two independent halves share a quarter of the units, and the
  estimation error is common to every seed and to the full support. So a
  seed's gap differs from x by an independent N(0, r_c²);
- the bound rule passes the cell when |x| + z\*_m √v_reg,c <= τ_c, with
  z\*_m = Φ⁻¹(1 - 0.05 / (2m)) over the m gated cells;
- a seed passes the cell when its side-A gap lies within ±τ_c;
- a_c,j = E[1{bound passes} p_c(x)^j] for j = 4 and 5, where p_c(x) is
  one seed's conditional pass probability, by adaptive quadrature;
- P(gate passes) = 5 ∏_c a_c,4 - 4 ∏_c a_c,5: every cell passes the
  bound rule and at least four of five seeds pass every cell.

Cells are treated as independent. For the bound-rule part that
understates the pass probability under any correlation between jointly
normal gaps (the Gaussian correlation inequality). The seed part is
priced by this conditional model, not by M6's `oc_4of5`, which gives a
faithful side-A score a standard deviation above the side-A upper bound.
Given a bound-rule pass, two or more seeds fail with probability at most
C(5, 2) × 0.05² = 0.025 on any basis. The Monte Carlo and
undefined-cell conditions of B2's pass rule are not priced. The Monte
Carlo rule can bind only where τ_c < 2.2 se_up, where the bound rule has
almost no power at four or more cells.

**Binding evaluation.** B2's 0.90 power requirement, its ladder and
this addendum's verdict use r_c = the arm-F point estimate and v_c =
v_reg,c = s²_gate,c, with τ_c and se_up from B2's own floor at floor
time and τ = 2.60632 × 2 / √(1 + 1/K) = 5.0870 (the uncapped k = 3
tolerance) in this addendum. Three other evaluations are reported and
decide nothing: the point gap variance s² with the registered bound
e_B2; r = 1 with e = 0, the audit's basis; and the bound rule times
M6's `oc_4of5`.

**The verdict this addendum records**, at uncapped tolerances, which
bound every capped surface's power from above:

- if no surface of four cells from any families reaches 0.90, d693's Q2
  flip fires: B2 is `WEAK_POWER_OR_VACUITY`;
- if a four-cell surface reaches 0.90 but no surface holding every
  concept family does, M6's ladder, which never prunes a family's last
  cell, stops B2 although the flip's four-cell test would not. The two
  ruled texts then disagree and the choice goes to Max;
- otherwise B2 is feasible, subject to its floor builder's own
  evaluation on B2's floor.

In the first two cases B2 stops and a decision is queued for Max. No
rescoped registration is written before he rules.

### Constants

| Constant | Value |
|---|---|
| Fit seed; draw seeds | 5200; 6200-6219 |
| Arm F, arm D replicates | 4,000; 1,000 |
| Arm R replicates | 0, 1, 2, … in order, at most 200, at least 60 |
| Arm R budget | 36 hours from arm R's first start, across resumes |
| Root seed | 20260930 |
| Stream words | [root, b, 0] arm F households; [root, b, 2] and [root, b, 3] arm R full-anchor and other half-samples; [root, b, 4] arm D; [root, 2^20] limits |
| Limit resamples; percentiles | 2,000; 5th and 95th, and 97.5th for upper limits |
| Defined share needed in arm F | 0.99 |
| Void share of in-replicate failures | above 0.10 of an arm |
| Design-ratio limit | 1.10 |
| Truth-agreement tolerance | 1e-9 relative |
| Identifier scale for copies | 1000 |

Arm R stops at 200 replicates or when its budget ends, whichever comes
first. At the budget it keeps the longest completed run of replicates
from 0. The rule depends on time alone.

### Output, checkpoint and stop rules

- The script writes one exclusive file,
  `docs/design/track_b_b0_1_planning_values.json`, and refuses to
  overwrite it. The record carries the repository head, the pushed
  branch head read before any PSID file, this block's SHA-256, the
  script's SHA-256, every opened PSID file's SHA-256, the runtime, the
  seeds and the checkpoint's event log.
- It runs from a clean worktree at the commit that adds this protocol,
  and only when that commit is the pushed branch head and this block
  hashes to the value the script holds.
- A replicate that raises is counted as failed with its exception class
  and leaves its arm. An arm with failures above the void share is void,
  and no cell then has planning values. If arm R has any failure, the
  record marks e as a lower bound for every cell.
- A memory or operating-system error inside a replicate is an
  interruption, not a replicate failure.
- A failure outside a replicate (a killed worker, a broken pool, memory,
  an interrupt) is an interruption, not a failure. The checkpoint, bound
  to this commit, this block's hash and the run's thread settings, is
  kept, the interruption is logged, and the same run resumes. A process that died without logging
  is recorded as such on resume. Replicates are deterministic, so a
  resumed run is the same run.
- Any other failure ends the run: the checkpoint is deleted, and the
  stage and exception class are published. The protocol is then revised
  in a new, dated version before any rerun.
- No definition above changes after any planning value is seen.
<!-- protocol-v2:end -->
