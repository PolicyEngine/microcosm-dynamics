# Track B B0.1 addendum: the frozen record B2 registers on

**Status: protocol frozen and planning values computed, 2026-10-01.
Max ruled d765, d781 and d782 on 2026-10-11 (section 2). On the
configuration they set, the six level cells reach 0.813 power, not the
0.952 d781 cites. Max confirmed the ruled surface the same day (d1342,
option A): B2's floor-build ladder decides (sections 11 and 13).**
This file is the post-ruling addendum that the B0.1 audit
(`docs/design/track_b_b0_1_audit.md`, section 13) calls for. It does
three things:

- it freezes elements 5-9 of design §5.2 for B2, and with the audit's
  frozen elements makes the complete record B2 registers on;
- it derives B2's planning values under a new protocol version, frozen
  in section 16 before any computation;
- it recomputes the named power procedure on the basis Max ruled.

At the commit that froze protocol v2 (`0550d2f`), sections 1-9 and
12-16 were complete. They hold every rule that decides B2's surface, its
pass rule and this addendum's verdict. Sections 10 and 11 were written
after the planning-value run, and section 15's record after the blinded
review. Sections 1, 12, 13 and 14 gained the run's results, one
correction it forced, the decisions it queues and the reads after the
freeze. None of these changes a rule. The protocol block in section 16
never changes.

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
  ratification (d765): the refit arm resamples household half-samples
  without replacement, not a bootstrap, because copied households defeat
  the sign gate's early stopping (sections 10 and 13).
- **What the run found.** Every one of the 16 cells has planning values
  (section 10). The law's estimation variance is large: 0.23 to 2.49
  times the truth statistic's sampling variance, by cell. Nine cells fail
  the survey-design check.
- **Verdict on the original d693 surface, before the 2026-10-11
  rulings.** On the ruled basis no surface that keeps every concept
  family reaches 0.90 power. The best reaches 0.331, while four level
  cells together reach 0.992 (section 11). B2 stops here. Before any
  candidate run, Max decides how to rescope it (d781) and how its
  standard error treats PSID's survey design (d782) (section 13).
- **The rulings of 2026-10-11** (section 2):
  - d781 (a) gates the six level cells;
  - d782 resamples design clusters for the standard error;
  - d765 ratifies the half-samples.

  Round-1 finding M2's rider adds a t critical value with the design's
  63 degrees of freedom (section 7).
- **Power on that configuration.** The six level cells reach 0.813 on the
  binding evaluation, against the 0.952 d781 cites on household
  resampling. Every evaluation that keeps the t value is below 0.90.
  Of the evaluations on the ruled configuration (household resampling,
  d781's basis, excepted), only the most lenient reaches it, at 0.907
  (section 11).
  - Section 16's rule does not stop B2: four of the six reach 0.964, so
    B2's floor and ladder would decide.
  - The ruling rested on 0.952, so B2 was held for Max, who confirmed
    the surface in d1342 (option A, section 2).

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

**The rulings of 2026-10-11.** Max ruled the three decisions this
addendum queued (section 13). The decision log records them as:

- **d765:** "ratify: household half-samples (without replacement) for B2's
  refit arm; the fixed-law arm stays a household bootstrap (Max in chat
  2026-10-11, guided walkthrough)".
- **d781:** "(a) rescope B2 to the six level cells (p50, p90 and zero rate
  by cohort; power 0.952); the other ten cells are scored and published
  report-only; B2's headline covers earnings levels and zero rates only;
  H and B3L rely on B2 for levels only (Max in chat 2026-10-11)".
- **d782:** "resample PSID sampling-error clusters within strata (Rao-Wu)
  for B2's registered standard error; the floor split and gate seeds'
  split stay household per d693 Q3 (Max in chat 2026-10-11)".

| Ruling | What it freezes | Where |
|---|---|---|
| d765 | Arm R's household half-samples stand, so the planning record's e and e_B2 are B2's registered estimation-variance values | Sections 7, 10 |
| d781 (a) | Element 6: B2's gate family is the six level cells; the other ten are report-only; the headline and what H and B3L may rely on | Sections 5, 13 |
| d782 | Element 8: se_boot resamples design clusters within strata (Rao-Wu); the floor and gate-seed splits stay household. With round-1 finding M2's rider, the critical value is Student t with the design's degrees of freedom | Sections 7, 8 |

d782's ruling text does not name the critical value. The t value came
from round-1 finding M2's rider, and Max saw it: d1342's question
described the ruled configuration as "d781 six level cells, d782 Rao-Wu
SE, t at 63 df", and he ruled option A on that configuration.

The 0.952 that d781 cites is household resampling's figure. On the
configuration the three rulings and the M2 rider set together, the six
level cells reach 0.813 on the binding evaluation, below 0.90 (section
11, "Power on the configuration Max ruled"). Section 16's rule would let
B2's floor and ladder decide. The ruling rested on 0.952, so B2 was held
for Max. He confirmed the ruled surface the same day:

- **d1342:** "A: proceed as ruled (d781 six level cells); B2's floor-build ladder prunes inside the six until power >= 0.90 with at least four cells; if it cannot, B2 stops at floor build before any candidate outcome and the choice among B-D returns to Max on B2's real tolerances (Max in chat 2026-10-11, guided walkthrough)".

So d781 (a) stands, and its ladder is section 5's, run on B2's own floor
inside the six. If no surface of four or more of the six reaches 0.90 on
that floor, B2 is `WEAK_POWER_OR_VACUITY` at floor build, before any
candidate outcome. Options B-D of d1342 (section 13) then return to Max,
priced on B2's real tolerances.

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
| 6. Critical cells | Rule frozen | Section 5; d781 (a): the six level cells, confirmed by d1342 (A) |
| 7. Numerical tolerances | Rule frozen | Section 6 |
| 8. Uncertainty treatment | Frozen | Section 7; d782: Rao-Wu se_boot, with Student t at the design's degrees of freedom |
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

**The ruled surface (d781 (a), 2026-10-11).** B2's gate family is the six
level cells: `earn_p50.older`, `earn_p50.prime`, `earn_p90.older`,
`earn_p90.prime`, `earn_zero_rate.older` and `earn_zero_rate.prime`.

- The other ten gateable cells are scored and published report-only, as
  pruned cells are below.
- B2's headline says its gate covers earnings levels and zero rates only,
  not changes, dispersion, mobility or persistence.
- H and B3L rely on B2 for levels only.
- Eligibility, the ladder and the guards below run on B2's own floor
  inside the six. The six span two concept families, log quantiles and
  zero rate, so the ladder can prune at most two cells before the
  four-cell guard binds.
- Of the six, `earn_zero_rate.older` carries the label "published
  candidate-3-law outcomes at boundaries 2008 and 2010" and the other five
  "published five-seed floor detail, no published candidate outcome".

On the ruled configuration the six reach 0.813 on the binding evaluation,
not the 0.952 d781 cites (section 11). Max confirmed the surface in
d1342 (option A, section 2). The ladder below runs inside the six on B2's
floor. If it ends below 0.90 or below four cells, B2 stops at floor build
and the choice returns to Max.

The rest of this section is the rule as d693 froze it. Under d781 its
candidate family is the six.

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
cells; here it counts B2's earnings cells. On d693's 16-cell surface,
with six eligible families, the ladder cannot go below six cells, so the
four-cell guard binds only if three or more families have no eligible
cell. Inside d781's six there are two families, so the guard can bind
after two prunes (above).

**If the ladder ends below 0.90, a guard fails, or ν is 0 after section
7's merges.** B2 is
`WEAK_POWER_OR_VACUITY` (design line 454). The floor artifact records
it, B2 stops, and a decision is queued for Max with the rescoping
options. Rescoping the surface or a tolerance cannot cure ν = 0, so
there the decision queued is how the critical value is set. No rescoped
or amended registration is written before he rules. This covers every
case d693's Q2 flip names.

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
- **Bootstrap standard error (d782).** se_boot,c = SD of the signed gap
  over 4,000 design replicates, with the law fixed and each person's
  projected paths fixed. A design replicate resamples PSID's
  sampling-error clusters (`ER31997`) within strata (`ER31996`) among
  the truth-support persons, by Rao-Wu.
  - **Two-cluster strata** follow arm D's `design_multiplicities` rule:
    one cluster is drawn and copied twice. That rule is applied through
    the root-parameterised copy section 13 specifies ("To B2"), never the
    pinned function, which reads protocol v2's root.
  - **Other strata** follow the stratum rule below, not arm D.
    - Arm D keeps a one-cluster stratum once.
    - It draws a stratum of three or more clusters with replacement.
      That is not Rao-Wu, and it understates the stratum's variance by
      (n_h - 1)/n_h.

  At the 2006 pseudo-origin every one of the 63 strata had exactly two
  clusters.

  **Arm D's rule is Rao-Wu only for two-cluster strata (Q6 round 2).**
  Applied to other strata it would go wrong:
  - a stratum with three or more is resampled by the ordinary bootstrap,
    which narrows the bound;
  - a stratum with one cluster adds no variance, which needs a
    certainty-unit justification.

  So B2's floor builder counts the strata among B2's truth-support persons
  by cluster count before any candidate run, and handles the other cases
  by this rule, fixed here (Q6 round 5):
  - **One cluster.** Such a stratum is merged into the nearest stratum
    by code among the strata with two or more clusters, the lower code on
    a tie. If no stratum has two or more clusters, all the one-cluster
    strata merge into one. All merges are applied together, before
    anything else, and the merged strata are then counted with their
    combined clusters.
  - **Three or more clusters.** Exact Rao-Wu, by integer copies. Each
    replicate draws n_h - 1 clusters with replacement in such a stratum,
    and each draw counts n_h/(n_h - 1). To keep counts whole, every
    stratum's multiplicities, including those of the two-cluster
    strata, are multiplied by L, the least common multiple of n_h - 1
    over the strata. A two-cluster stratum's drawn cluster is then
    copied 2L times, and a draw in a stratum of n_h clusters
    L·n_h/(n_h - 1) times.
  - **Scale.** Scaling every person's copies by the same L leaves
    weighted quantiles and weighted rates unchanged, so the gated level
    cells are unaffected. The report-only mobility cells, which bin by
    midpoint weighted rank, are not exactly invariant to it.
  - **When every stratum has two clusters**, as at the 2006 pseudo-origin,
    L is 1 and the rule is arm D's.

  ν is Σ_h (n_h - 1) after the merges. The floor builder publishes the
  counts, the merges and L before any candidate run.

  The floor and gate-seed splits stay household (d693 Q3, d782).
- **The household bootstrap.** se_up,c uses its own 4,000 replicates:
  multinomial multiplicities over all 2011 full-anchor households (equal
  probabilities, as many draws as households, the seed below),
  households without a domain person included. se_up stays household
  because a_c below is measured in household se_up units (section 10).
- **Copying.** In both bootstraps each person whose household or cluster
  has multiplicity c is copied c times under new identifiers, truth rows
  and every draw's projected rows alike, by this addendum's
  `copy_persons`. Weights are never multiplied instead, because the
  mobility cells bin by midpoint weighted ranks.
- **Design degrees of freedom.** ν = Σ_h (n_h - 1) over the strata among
  B2's truth-support persons after the stratum rule's merges, n_h being
  stratum h's cluster count after them. A one-cluster stratum merged
  into another adds its cluster there, and so one degree of freedom. If
  ν is 0 after the merges, which needs every truth-support person in one
  cluster, t\*_m,ν is undefined and B2 stops at floor build as
  `WEAK_POWER_OR_VACUITY`. The floor builder counts ν from
  the design variables before any candidate outcome and publishes the
  strata counted by cluster count, as `design_summary` does. At the 2006
  pseudo-origin ν was 63.
- **Registered standard error.** se_c = √(se_boot,c² + a_c × se_up,c²),
  where a_c is the cell's registered estimation-variance ratio from
  section 10: e_B2,c, plus the transported cross term where section 16's
  rule adds it. a_c is never negative, so se_c is at least se_boot,c.
  d765 ratified the half-samples behind e_B2.
- **Bound (round-1 M2).** |g_c| + t\*_m,ν × se_c, with t\*_m,ν the
  two-sided simultaneous 95% value over the m gated cells from Student's
  t with ν degrees of freedom, t_ν⁻¹(1 - 0.05/(2m)). It replaces d693's
  normal z\*_m because the design-based se_boot is estimated from about ν
  degrees of freedom. At m = 6 and ν = 63 it is 2.724, against
  z\*_6 = 2.638. Giving the whole of se_c ν degrees of freedom is
  conservative, since a_c × se_up² is a registered constant.
- **Monte Carlo error.** The SD over the K = 20 draws of the per-draw
  signed gap (ln(P_k/T) for `log_ratio` cells, P_k - T otherwise),
  divided by √K, must be below tol_c/10 (design line 302). A cell that
  fails cannot pass. Side-A seeds carry no Monte Carlo rule, as in M6.
- **Undefined replicates.** A gated cell with more than 1% of its
  design or household replicates undefined cannot pass.
- **Survey design.** d693 ruled household resampling. Section 16's design
  rule did not hold at the pseudo-origin (section 10), and d782 resolved
  the choice it sent to Max: the registered standard error resamples
  design clusters, as above.
- **Side A.** Each gate seed's side-A statistics come from the
  full-domain projection's K draws, restricted to side-A persons. B2
  does not re-project each half.
- **Seeds.** B2 uses protocol v2's seeds and streams, with a new root.
  - The scoring bootstrap's root seed is 20261002. Household replicate b
    draws its multiplicities from stream [root, b, 0], and design
    replicate b its clusters from [root, b, 4] (d782).
  - Candidate 3's law is fitted with seed 5200 and projected with draw
    seeds 6200-6219 (K = 20), as in protocol v2 and the selectors.
  - Floor seeds are 0-99 and gate seeds 0-4 (section 4).

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
   - the bound lies within tolerance, |g_c| + t\*_m,ν × se_c <= tol_c
     (section 7);
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
   It counts the design strata by cluster count, applies section 7's
   stratum rule, and publishes the counts, the merges, L and ν before any
   candidate run. If ν is 0, B2 stops here as `WEAK_POWER_OR_VACUITY`
   (sections 5 and 7).
5. It applies eligibility, the ladder and the guards (section 5) inside
   the ruled surface (d781). Power comes from the ruled binding
   evaluation (`scripts/track_b_b0_1_ruled_power.py`, section 11):
   - r_c, the 95th percentile of d_c and s²_gate,c from section 10;
   - ν, and τ_c = tol_c / se_up,c, from B2's own floor;
   - t\*_m,ν as the critical value.

   The design ratio needs projections, so the builder cannot measure it
   at B2's origin; it uses the 2006 value.
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

**The run.** Protocol v2 ran once. The script started at 03:58:23 UTC on
2026-10-01 from a clean worktree at `0550d2f`. Before it opened any PSID
file it confirmed that `0550d2f` was this branch's pushed head. It
finished at 07:23:27 UTC, after 12,304 seconds, with no interruption and
no resume, and deleted its checkpoint unread. Its record,
`docs/design/track_b_b0_1_planning_values.json`, carries:

- the protocol block's SHA-256 (section 16) and the script's SHA-256;
- the SHA-256 of each of the 74 PSID files it opened: the family files of
  collection waves 1969-2011 and the cross-year individual file, each
  byte-identical to the audit's pinned read set (`b2_read_set_sha256`);
- NAWI read through its 2006 key, with prefix and mapping hashes equal to
  the selectors' pins;
- the runtime, seeds and thread settings.

`tests/test_track_b_b0_1_addendum_record.py` checks each of these
against the repository.

**The protocol's checks all passed.**

- Source reproduction: 321,500 fit-input rows, 23,134 full-anchor persons
  and 13,542 domain persons at B2's 2010 boundary, equal to the frozen
  record.
- The forest-free refit reproduced both gates' classifier state and
  probability surfaces, and the projections of draw seeds 6200 and 6201.
- Arm F used 4,000 replicates and arm D 1,000. Arm R used 200, the most
  the protocol allows, inside its budget. No replicate failed, so no arm
  is void and e is not a lower bound. In every arm R replicate the truth
  statistics on the refit side and the fixed-law side of the same kept
  frame agreed within 1e-9, relative.
- The record's outcome-blind flags are constants the script writes, not
  checks. The evidence that nothing after 2010 was read or recorded is
  elsewhere, with one exception. `transport.support_2010` copies B2's
  scored-support counts for reference years 2012 and 2014 from the frozen
  record `docs/design/track_b_b0_1_counts.json` (protocol input 7). They
  are presence counts, not split by earnings sign, and the record holds
  nothing else about those years. The evidence:
  - the read guard refuses any other PSID open before it happens;
  - the opened files match the audit's pins and include no wave after
    2011;
  - the record-shape check refuses any key outside the frozen
    allow-list.
- One quirk, moot here. A guard refusal raised inside a worker is an
  `OSError`, which the script treats as an interruption to resume, not
  as a failure. Workers open no PSID file, so it could not arise.

**At the pseudo-origin.** The fit used 294,603 rows. The full anchor held
22,102 persons in 8,289 households and the domain 12,837 persons. The
law's anchor forward pairs numbered 105,738, against 113,823 at B2's
origin. Arm D resampled 11,176 truth-support persons in 63 strata, each
with two clusters.

**Values.** Units are each cell's se_up. Columns: the shared-anchor ratio
r and the estimation variance e, each with its 5th-95th percentile
range; e's 97.5th-percentile limit; the transport factor f; B2's
registered e_B2; the point gap variance s²; the gating variance s²_gate;
and the design ratio d with its 95th percentile.

| Cell | r (5th-95th) | e (5th-95th) | e upper | f | e_B2 | s² | s²_gate | d (95th) |
|---|---|---|---:|---:|---:|---:|---:|---|
| `earn_autocorr_lag1` | 1.010 (0.998-1.022) | 1.059 (0.821-1.307) | 1.362 | 1.000 | 1.362 | 2.079 | 2.383 | 1.074 (1.119) |
| `earn_autocorr_lag2` | 0.984 (0.976-0.991) | 0.332 (0.264-0.396) | 0.409 | 1.000 | 0.409 | 1.300 | 1.379 | 0.950 (0.989) |
| `earn_dlog_mean.older` | 0.984 (0.975-0.994) | 0.728 (0.578-0.887) | 0.915 | 1.000 | 0.915 | 1.697 | 1.885 | 1.124 (1.166) |
| `earn_dlog_mean.prime` | 0.971 (0.963-0.979) | 0.412 (0.328-0.492) | 0.508 | 1.000 | 0.508 | 1.355 | 1.454 | 1.076 (1.123) |
| `earn_dlog_sd.older` | 1.008 (0.997-1.021) | 0.946 (0.716-1.187) | 1.239 | 1.000 | 1.239 | 1.963 | 2.256 | 1.049 (1.092) |
| `earn_dlog_sd.prime` | 1.045 (1.032-1.058) | 2.488 (2.032-2.988) | 3.087 | 1.000 | 3.087 | 3.581 | 4.191 | 1.112 (1.158) |
| `earn_mob_h1_diag` | 1.016 (1.004-1.029) | 0.691 (0.551-0.838) | 0.870 | 1.000 | 0.870 | 1.723 | 1.907 | 1.096 (1.139) |
| `earn_mob_h2_diag` | 1.059 (1.048-1.071) | 0.529 (0.422-0.641) | 0.664 | 1.000 | 0.664 | 1.651 | 1.789 | 1.002 (1.043) |
| `earn_p10.older` | 1.045 (1.023-1.067) | 1.041 (0.841-1.237) | 1.280 | 1.000 | 1.280 | 2.133 | 2.393 | 0.916 (0.956) |
| `earn_p10.prime` | 1.208 (1.176-1.241) | 1.796 (1.430-2.151) | 2.218 | 1.000 | 2.218 | 3.255 | 3.714 | 1.159 (1.215) |
| `earn_p50.older` | 0.737 (0.725-0.750) | 0.418 (0.342-0.490) | 0.505 | 1.000 | 0.505 | 0.961 | 1.054 | 1.214 (1.259) |
| `earn_p50.prime` | 0.754 (0.743-0.764) | 0.260 (0.213-0.305) | 0.317 | 1.000 | 0.317 | 0.829 | 0.891 | 1.122 (1.167) |
| `earn_p90.older` | 0.660 (0.648-0.674) | 0.328 (0.267-0.388) | 0.398 | 1.000 | 0.398 | 0.764 | 0.840 | 1.027 (1.069) |
| `earn_p90.prime` | 0.686 (0.672-0.698) | 0.234 (0.183-0.284) | 0.297 | 1.000 | 0.297 | 0.704 | 0.771 | 1.027 (1.069) |
| `earn_zero_rate.older` | 0.706 (0.691-0.720) | 0.235 (0.190-0.283) | 0.293 | 1.000 | 0.293 | 0.733 | 0.799 | 1.167 (1.210) |
| `earn_zero_rate.prime` | 0.787 (0.772-0.803) | 0.305 (0.243-0.368) | 0.381 | 1.000 | 0.381 | 0.924 | 1.008 | 0.947 (0.986) |

Diagnostics, which decide nothing:

| Cell | Cross term (5th-95th) | Simulation share of Var(δ) | Floor σ / (2 × truth SD) | Monte Carlo error / se_up |
|---|---|---:|---:|---:|
| `earn_autocorr_lag1` | -0.009 (-0.233-0.228) | 0.17 | 0.93 | 0.221 |
| `earn_autocorr_lag2` | -0.060 (-0.215-0.087) | 0.22 | 1.05 | 0.133 |
| `earn_dlog_mean.older` | 0.050 (-0.149-0.247) | 0.15 | 0.97 | 0.168 |
| `earn_dlog_mean.prime` | -0.059 (-0.232-0.109) | 0.22 | 1.00 | 0.186 |
| `earn_dlog_sd.older` | 0.099 (-0.231-0.435) | 0.20 | 0.95 | 0.234 |
| `earn_dlog_sd.prime` | 0.121 (-0.279-0.526) | 0.11 | 1.02 | 0.192 |
| `earn_mob_h1_diag` | -0.336 (-0.562--0.115) | 0.17 | 1.05 | 0.163 |
| `earn_mob_h2_diag` | -0.135 (-0.321-0.057) | 0.18 | 0.94 | 0.194 |
| `earn_p10.older` | -0.149 (-0.400-0.101) | 0.12 | 0.94 | 0.160 |
| `earn_p10.prime` | -0.188 (-0.536-0.175) | 0.13 | 0.76 | 0.214 |
| `earn_p50.older` | -0.052 (-0.163-0.061) | 0.08 | 0.96 | 0.108 |
| `earn_p50.prime` | -0.065 (-0.169-0.032) | 0.09 | 0.99 | 0.059 |
| `earn_p90.older` | 0.072 (-0.017-0.159) | 0.10 | 1.07 | 0.085 |
| `earn_p90.prime` | 0.024 (-0.063-0.115) | 0.14 | 1.03 | 0.102 |
| `earn_zero_rate.older` | 0.015 (-0.067-0.098) | 0.21 | 0.94 | 0.109 |
| `earn_zero_rate.prime` | 0.053 (-0.074-0.181) | 0.21 | 1.02 | 0.127 |

**Reading the values.**

- Every cell has planning values. Each floor is eligible at the
  pseudo-origin, and every replicate of every arm is defined for every
  cell.
- r is below 0.80 for the p50, p90 and zero-rate cells, where the
  projection and the truth move together under resampling. It is 0.97 to
  1.21 for the others, and above 1 for seven of them. The audit's
  full-support standard error is therefore not an upper bound for those
  cells (section 12). No rule here depends on it being one: B2's
  registered standard error uses the measured bootstrap gap standard
  error (section 7).
- e, the law's estimation variance, runs from 0.23 to 2.49 times the
  truth statistic's sampling variance. It is largest for
  `earn_dlog_sd.prime` (2.49) and `earn_p10.prime` (1.80).
- f is 1 for every cell. B2's support per anchor forward pair is no
  larger than the pseudo-origin's, so the rule's floor of 1 applies and
  e_B2 equals e's upper limit.
- No cross term's 5th percentile is above zero, so none enters s²_gate.
  For `earn_mob_h1_diag` the whole range is below zero: there, estimation
  and sampling errors offset, and leaving the term out overstates the
  cell's gap variance.
- Nine of the 16 cells have a design-ratio 95th percentile above 1.10,
  up to 1.259 for `earn_p50.older`. Section 16's design rule therefore
  does not hold. Household resampling understates these cells' sampling
  variance under PSID's design, and the choice between inflating B2's
  standard error and resampling design clusters goes to Max (d782,
  section 13).
- Diagnostics. The K draws' simulation noise is 8% to 22% of Var(δ).
  The floor's σ over twice the truth deviation's SD is 0.76 to 1.07,
  near 1 except for `earn_p10.prime`. The full sample's Monte Carlo
  error is 0.06 to 0.23 se_up.

**What the values do not establish.**

- They are measured from 2006 to 2008 and 2010. Those truth years fall
  in a recession, and neither r's nor e's transport to 2012 and 2014 is
  tested.
- e comes from household half-samples (d765). For a smooth statistic a
  half-sample's deviation from the full sample has the full sample's
  variance. For this law, whose sign gates stop early, that is not
  established in either direction.
- The cross term is left out unless resolved positive.
- d's limits cover the bootstrap's Monte Carlo error only. A variance
  built from 126 clusters in 63 strata has about 63 degrees of freedom,
  so d itself is uncertain by roughly ±9%. Cells near the 1.10 limit
  could fall on either side of it.
- Persons outside the full anchor are clustered by their household at
  their last present wave up to 2007, an approximation to the panel's
  household structure.
- M6's published floor was not used, even as an illustration.
- The values say nothing about any candidate outcome or about whether
  candidate 3 transports.

## 11. Power on the ruled basis and the verdict

The first part of this section, through d781's figures, is the verdict
on the original d693 surface: all 16 cells, every concept family. It
was reached before the 2026-10-11 rulings. "Power on the configuration
Max ruled", at the end of this section, is the current case.

`scripts/track_b_b0_1_addendum_power.py` computes
`docs/design/track_b_b0_1_addendum_power.json` from the planning-value
record alone, by the named procedure (section 16), at the nominal
uncapped k = 3 tolerance, τ = 5.0870 se_up. That is the k = 3 tolerance
of a half-normal floor, in se_up units. B2's realized tolerance in
those units depends on its floor: M6's floors gave tolerance over σ of
2.35-2.64 against the nominal 2.61, and σ over twice the truth
deviation's SD was 0.76-1.07 at 2006 (section 10). So the figures are
nominal, not bounds. A cap only lowers a tolerance.
`scripts/track_b_b0_1_addendum_tables.py` renders the tables below from
the two records, and the record test requires them verbatim.

| Evaluation | All cells with planning values | M6-retained six | Best four cells | Best surface with every family |
|---|---:|---:|---:|---:|
| Binding | 0.000 | 0.000 | 0.992 | 0.331 |
| Point variance (sensitivity) | 0.000 | 0.004 | 0.995 | 0.369 |
| r = 1, e = 0 (sensitivity) | 0.584 | 0.917 | 0.962 | 0.917 |

On the binding evaluation, all 16 cells together and the six
M6-retained cells have essentially no power. The best four-cell surface,
`earn_p50.prime`, `earn_p90.older`, `earn_p90.prime` and
`earn_zero_rate.older`, reaches 0.992. So d693's Q2 flip, which asks
whether four cells have room, does not fire.

Section 5's ladder can end only on a surface that keeps a cell of every
concept family. The best and worst such surfaces of each size, on the
binding evaluation:

| Gated cells | Surfaces | Best p_gate | Worst p_gate |
|---:|---:|---:|---:|
| 6 | 192 | 0.331 | 0.000 |
| 7 | 960 | 0.294 | 0.000 |
| 8 | 2,320 | 0.262 | 0.000 |
| 9 | 3,520 | 0.231 | 0.000 |
| 10 | 3,652 | 0.202 | 0.000 |
| 11 | 2,668 | 0.113 | 0.000 |
| 12 | 1,375 | 0.059 | 0.000 |
| 13 | 490 | 0.016 | 0.000 |
| 14 | 115 | 0.004 | 0.000 |
| 15 | 16 | 0.000 | 0.000 |
| 16 | 1 | 0.000 | 0.000 |

The best is six cells: `earn_autocorr_lag2`, `earn_dlog_mean.prime`,
`earn_dlog_sd.older`, `earn_mob_h2_diag`, `earn_p90.prime` and
`earn_zero_rate.older`, at 0.331. At six cells its dispersion cell alone
passes the bound rule with probability 0.546, its mobility cell 0.756,
its change-mean cell 0.886 and its autocorrelation cell 0.910. Every
family-complete surface needs a dispersion and a mobility cell, and the
smallest gating variances in those families are 2.256 and 1.789 se_up²,
against 1 on the audit's basis. On point variances the best family
surface reaches 0.369. On the audit's basis (r = 1, e = 0) it reaches
0.917, the audit's six-cell figure. The difference is the law's
estimation variance, which the audit could not measure.

**Verdict: stopped by the family floor.** On the binding evaluation a four-cell surface reaches 0.90 but no surface holding every concept family does.

d693's Q2 flip does not fire, because four cells have room. But Q1's
ladder never prunes a family's last cell, so at the nominal tolerance it
cannot end at 0.90. Under section 5, B2 is then `WEAK_POWER_OR_VACUITY`
at its floor build, and section 16's verdict rule sends the case to Max.
B2 stops here. Decision d781 asks Max how to rescope it, and no rescoped
registration is written before he rules (section 13).

The verdict does not turn on the nominal tolerance. With τ 5% and 10%
above nominal, the best family surface reaches 0.462 and 0.585.

The protocol says the Monte Carlo rule can bind only where τ_c < 2.2
se_up. With the measured Monte Carlo errors, up to 0.234 se_up for
`earn_dlog_sd.older`, the threshold is about 2.34 se_up. That changes
nothing at the nominal tolerance.

The design rule did not hold either (section 10). With each over-limit
cell's sampling variance inflated by its design ratio's 95th percentile,
squared, the verdict is the same: the best four-cell surface reaches
0.975 and the best family surface 0.293 (the power record's
`decision_illustrations`).

**Figures that need no planning value**, fixed before the run. On the
audit's basis (r = 1, no estimation error), at uncapped k = 3
tolerances:

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
0.001 at every size. Section 10 measured r above 1 for seven cells, so
this basis is not an upper bound for them.

### Power on the configuration Max ruled

After the rulings of 2026-10-11 (section 2),
`scripts/track_b_b0_1_ruled_power.py` recomputes the named procedure on
the configuration they set. It writes
`docs/design/track_b_b0_1_ruled_power.json` from the planning-value record
alone. The configuration is:

- the six level cells (d781 (a));
- the Rao-Wu standard error (d782);
- Student t with the design's ν = 63 degrees of freedom (round-1 M2);
- the half-sample estimation variances (d765).

Units are each cell's household se_up, as above. The model changes protocol
v2's evaluation in three places:

- **The gap's sampling variance.** Under Rao-Wu it is (r_c × d_c)², with
  d_c the cell's design ratio (section 10). The full-support gap is
  x ~ N(0, (r_c d_c)² + e_c), with e_c the estimation part of protocol
  v2's variance: s²_gate,c - r_c² on the binding evaluation, and
  s²_c - r_c² on the point-variance sensitivity.
- **The registered variance.** It is (r_c d_c)² × W + a_c, with
  W ~ χ²_ν/ν independent of x: B2 estimates the Rao-Wu part with ν degrees
  of freedom, and a_c is a registered constant. a_c is s²_gate,c - r_c² on
  the binding evaluation, as in protocol v2, and e_B2,c on the
  point-variance sensitivity.
- **The critical value.** The bound rule passes when
  |x| + t\*_m,ν √(registered variance) <= τ_c.

Each side-A seed's gap, given x, stays N(x, r_c²). The seed split is a
household split of the realized sample, so its spread is the household
resampling variance whatever the design.

The binding evaluation takes d_c at its 95th percentile, the design
rule's own statistic. With ν infinite, d = 1 and z\*, the model is
protocol v2's evaluation term for term, and the six cells return 0.952,
the figure d781 cites.

| Evaluation | P(gate passes) | P(bound rule passes) |
|---|---:|---:|
| Binding: d at its 95th percentile, gating variances, t with ν df, se_boot estimated | 0.813 | 0.813 |
| se_boot treated as known | 0.821 | 0.821 |
| d at its point estimate | 0.854 | 0.854 |
| Point variances, e_B2 registered | 0.841 | 0.841 |
| Normal z\* in place of t, se_boot known | 0.852 | 0.852 |
| Side-A seeds spread by r × d | 0.813 | 0.813 |
| Most lenient: d point, point variances, z\*, se_boot known | 0.907 | 0.907 |
| Household resampling (d = 1, z\*): d781's basis | 0.952 | 0.952 |

**The six together fall short of 0.90.** On the binding evaluation they
reach 0.813, and every evaluation that keeps the t value is below 0.90.
Of the evaluations on the ruled configuration (household resampling,
d781's basis, excepted), only the most lenient combination reaches the
bar, at 0.907. It drops the t value, the upper design ratios and the
gating variances together.

- `earn_p50.older` is the weak cell. It has the largest design ratio
  (95th percentile 1.259) and the largest gap variance. On its own it
  passes the bound rule with probability 0.892 at six cells.
- Given a bound-rule pass, the seed conjunction fails with probability
  below 10⁻⁶ on every evaluation, so more gate seeds would change
  nothing.
- The six gaps' arm-F correlations are at most 0.18, so a
  correlation-aware simultaneous critical value should gain little. That
  gain was not computed.

**Verdict under section 16's rule: feasible, subject to B2's floor.** The
rule applied to the ruled surface does not stop B2. Its families are log
quantiles and zero rate, and section 5's four-cell guard applies. Four of
the six cells keep both families and reach 0.964.

So under d781 (a), B2's floor builder runs section 5's ladder inside the
six, on B2's own floor:

- over all 720 pruning orders it clears 0.90 in 306 on the binding
  evaluation, and in all 720 on the most lenient;
- in the other 414 it prunes to three cells and fails the four-cell guard,
  and B2 is `WEAK_POWER_OR_VACUITY` at floor build, before any candidate
  run;
- B2's floor fixes the order. Nothing makes the orders equally likely, so
  306 of 720 is a count, not a probability.

Every surface of four or more of the six that keeps both families, at the
nominal uncapped tolerance:

| Gated cells | Dropped | Binding | Most lenient |
|---:|---|---:|---:|
| 6 | none | 0.813 | 0.907 |
| 5 | `earn_p50.older` | 0.926 | 0.972 |
| 5 | `earn_p50.prime` | 0.864 | 0.933 |
| 5 | `earn_zero_rate.older` | 0.856 | 0.928 |
| 5 | `earn_zero_rate.prime` | 0.852 | 0.926 |
| 5 | `earn_p90.older` | 0.845 | 0.923 |
| 5 | `earn_p90.prime` | 0.842 | 0.922 |
| 4 | `earn_p50.older`, `earn_p50.prime` | 0.964 | 0.988 |
| 4 | `earn_p50.older`, `earn_zero_rate.older` | 0.956 | 0.984 |
| 4 | `earn_p50.older`, `earn_zero_rate.prime` | 0.952 | 0.982 |
| 4 | `earn_p50.older`, `earn_p90.older` | 0.946 | 0.979 |
| 4 | `earn_p50.older`, `earn_p90.prime` | 0.944 | 0.978 |
| 4 | `earn_p50.prime`, `earn_zero_rate.older` | 0.903 | 0.951 |
| 4 | `earn_p50.prime`, `earn_zero_rate.prime` | 0.899 | 0.949 |
| 4 | `earn_p50.prime`, `earn_p90.older` | 0.893 | 0.947 |
| 4 | `earn_p50.prime`, `earn_p90.prime` | 0.891 | 0.946 |
| 4 | `earn_p90.older`, `earn_zero_rate.older` | 0.886 | 0.943 |
| 4 | `earn_p90.prime`, `earn_zero_rate.older` | 0.884 | 0.942 |
| 4 | `earn_p90.older`, `earn_zero_rate.prime` | 0.883 | 0.941 |
| 4 | `earn_p90.prime`, `earn_zero_rate.prime` | 0.880 | 0.940 |
| 4 | `earn_p90.older`, `earn_p90.prime` | 0.875 | 0.938 |

These figures are nominal, like those above. B2's floor fixes its real
tolerance. For these six cells, M6's realized tolerance/σ (2.35-2.64,
against 2.61) and the 2006 floor-to-bootstrap ratios (0.94-1.07) put it
roughly 15% below to 8% above nominal. Binding gate power of the surfaces
decision d1342 names, at tolerances scaled by those amounts:

| Surface | τ × 0.85 | τ × 0.92 | τ × 1.00 | τ × 1.08 |
|---|---:|---:|---:|---:|
| The six, before any pruning | 0.382 | 0.617 | 0.813 | 0.921 |
| B: without `earn_p50.older` | 0.620 | 0.808 | 0.926 | 0.976 |
| C1: without both medians | 0.767 | 0.895 | 0.964 | 0.989 |
| C2: without `earn_p50.older` and `earn_zero_rate.older` | 0.743 | 0.879 | 0.956 | 0.986 |
| D: the six at k = 3.26 | 0.557 | 0.763 | 0.901 | 0.963 |

The six cells Max ruled on reach 0.813, not the 0.952 that d781 cites.
The protocol would not stop B2 here, but the ruling rested on that
figure. So B2 was held, and decision d1342 asked Max to confirm the ruled
surface or change it (section 13). He confirmed it the same day: option
A, proceed as ruled (section 2).

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
| N1 | Audit §1 qualified the side-A figure by its standard error. After the run it calls that standard error a reference point, not a bound (below); the pinned strings follow |
| N2 | Audit §5.4 and §9.2 make the floor-equality claims conditional on a person split. Under the ruled household split the gating floor is new, and the person-split floor is a non-gating check run by the comparator (section 9) |
| N3 | Audit Q2 states the cost: the tolerance is about 5.1 standard errors wide on full support against about 3.6 on side A, about 1.4 times wider |
| N4 | `select_m6_qstar_train_only.py:645` restored in audit §4.3 and §15.1 |
| N5 | Audit §5.5 states that the inventory covers tracked files only. The review root leaves every listed file out whole, and section 15 adds the paths the inventory cannot see |
| N6 | The audit-record test now pins the prose-only figures; audit §11.3 and Q4 give the bands by cohort and add the side-A Kish band |
| N7 | Audit §2 says element 1 freezes the wage vintage and why |

The review of this addendum's own draft found two more points in the
audit, both fixed there: §10 left out M6's requirement that all five
seeds be valid, and §11.2's per-cell room figures were unlabelled.

**After the run: the audit's standard-error "upper bounds" are not
bounds.** Audit §11 says a faithful cell's full-support gap standard
error is "at most" σ·√(1 + 1/K)/2, because the anchor-explained part of
the sampling variation cancels in the gap. Over household resamples with
the law and paths fixed, the gap's variance is Var(T) + Var(P̄) -
2 Cov(T, P̄). It stays within the audit's figure only if the covariance
offsets the projected statistic's own resampling variance, up to
Var(T)/K, and nothing guarantees that. At the 2006 pseudo-origin r is
above 1 for seven of the 16 cells, up to 1.21 for `earn_p10.prime`
(section 10). Audit sections 1, 11 and Q2 now say so. Its figures on that basis, and the
"r = 1, e = 0" rows here, are reference points, not bounds. No rule in
this addendum relies on them: B2's registered standard error is
measured (section 7), and the binding evaluation uses the measured r.

## 13. Preconditions, open decisions and handoffs

**B2 may register only when all of these hold:**

- this addendum is merged with its planning values, and its Q6 review
  counted (section 15);
- Max has ruled on d781, because section 11's verdict is not
  "feasible", and on d782, because section 16's design rule did not
  hold; and any rescoped registration that follows his rulings is
  written and reviewed before any candidate run. **Ruled 2026-10-11:**
  d781 (a) and d782 Rao-Wu (section 2);
- Max has ratified the refit arm's half-sample resampling (d765), or
  ruled otherwise (below). **Ratified 2026-10-11** (section 2);
- Max has ruled on d1342. On the ruled configuration the six level cells
  reach 0.813, not the 0.952 d781 rests on (section 11, "Power on the
  configuration Max ruled"). Any registration that follows is written and
  reviewed before any candidate run. **Ruled 2026-10-11:** option A,
  proceed as ruled (section 2);
- a B1 run has passed: v1 `REPRODUCED`, or v2
  `RECONSTRUCTED_REPRODUCTION` (d622). A v2 pass carries its weaker
  label, "reconstructed reproduction (weaker than bit-for-bit)", into
  B2's registration and every downstream disclosure. A
  `BASELINE_REPLAY_MISMATCH` stops B2 (design line 451). **Passed
  2026-10-11:** B1 v2 returned `RECONSTRUCTED_REPRODUCTION`. All four
  conditions are exact, with zero differences. The registration is issue
  #42 comment 6110674288 and the result comment 6113379406. The result
  discloses one launcher deviation: its shell ended with the operator's
  session while the run went on to complete, so the exit code was not
  captured. B1's raw output stays sealed until B2 registers, and no B1
  run artifact is committed to this repository.

**Decisions queued for Max.** None blocks this addendum's merge. Each
blocked B2's registration. d765, d781 and d782 were ruled on 2026-10-11
(section 2). d1342, queued after those rulings, was ruled the same day
(option A, section 2). No decision is open.

- **d765, queued before the run.** d693's Q5 rider says the two planning
  values come from "one pseudo-origin household bootstrap". Arm F is a
  household bootstrap. Arm R, which refits the law, resamples household
  half-samples without replacement, for the reason and evidence in
  section 16, step 6. The alternative is a new protocol version with a
  with-replacement refit arm.

  That evidence comes from one run of the check, on 2026-10-01 at
  03:11:47 UTC, before the freeze. The command was
  `gate_leak_check.py <worktree> 4000 24`, with two fit jobs, run from a
  scratch copy on the runtime of section 16. Its output, with warnings
  removed, is `docs/design/track_b_b0_1_gate_leak_check.txt` verbatim.
  `scripts/track_b_b0_1_gate_leak_check.py` is that copy after black's
  formatting and ruff's automatic fixes, committed in `0550d2f`. It was
  not rerun after them. The refit-scheme rule was written down at
  03:15:19 UTC, before the comparison was read.
- **d781: how to rescope B2.** Section 11's verdict stops B2. Both
  ruled texts lead there: the flip does not fire, and the ladder makes B2
  `WEAK_POWER_OR_VACUITY`. The options, in no order:
  - (a) gate only the six level cells, `earn_p50` and `earn_p90` by
    cohort and `earn_zero_rate` by cohort, the largest surface that
    reaches 0.90 (0.952). The other ten cells are scored and published
    report-only, and B2's headline says its gate covers earnings levels
    and zero rates, not changes, dispersion, mobility or persistence. H
    and B3L may rely on B2 only for what it gates. This is the proposed
    default;
  - (b) gate a smaller surface that keeps one dynamic family, such as
    `earn_autocorr_lag2`, `earn_p90.prime` and `earn_zero_rate.older`
    (0.946). No surface with four or more families reaches 0.90;
  - (c) keep B2 `WEAK_POWER_OR_VACUITY` and unadmitted. H and B3L then
    stay blocked until another route is registered (design line 454);
  - (d) amend d693's Q2 settings, which design §5.3 and §7 allow before
    any candidate result (design lines 308, 454). Two forms:
    - **A wider tolerance on full support.** The best surface that keeps
      every family reaches 0.824 at k = 4 (a tolerance 1.23 times as wide
      as k = 3's) and 0.975 at k = 5 (1.46 times). It reaches 0.90 at
      k = 4.32, about 1.30 times as wide. A wider tolerance costs
      sensitivity to a misspecified candidate. The caps, ln 1.5 and
      0.15, may bind at these widths, and only B2's floor can show
      that.
    - **Another scoring basis.** M6's seed rule alone, with the bound
      rule reported but not gating, gives the best family surface
      0.993 on the same model. It drops the bound rule, which design
      §5.2 requires of every empirical gate, so it needs a design
      amendment as well as a change to Q2.

  The proposed default is (a). It keeps the ruled k = 3 sensitivity on
  the cells that can carry it. (d) keeps every family, at the cost of a
  tolerance about 1.30 times as wide. Under (a), (b) or (d), B2's
  floor builder still runs section 5's ladder on B2's own floor, inside
  the rescoped surface, and may prune further.
- **d782: how B2's standard error treats PSID's design.** The options:
  - (a) resample PSID's sampling-error clusters within strata (Rao-Wu,
    as arm D did) for se_boot, while the floor and gate-seed splits stay
    household (Q3). This measures B2's own design effect at its own
    origin. This is the proposed default;
  - (b) inflate the household se_boot by each cell's 2006 design ratio,
    a third transported planning value;
  - (c) keep household resampling, overriding section 16's rule.

  At the 2006 ratios either (a) or (b) costs about one cell: the largest
  surface that reaches 0.90 falls from six cells to five. That figure
  leaves out two things:
  - d itself is uncertain by about ±9% (section 10), and (b) multiplies
    by it;
  - under (a), B2's design-based se_boot has about 63 degrees of
    freedom, so the normal z\* under-covers. At m = 6 the t value with
    63 degrees of freedom is 2.724, against z\* = 2.638. A registration
    under (a) should use the t value.

- **d1342: confirm or change B2's surface after the ruled power.**
  **Ruled 2026-10-11: option A, proceed as ruled** (section 2). Queued
  2026-10-11, after the three rulings. The six level cells reach
  0.813 on the binding evaluation and
  0.907 on the most lenient (section 11).
  Section 16's rule would let B2's floor and ladder decide, but d781 rests
  on 0.952. The options, in no order, with binding and most lenient power
  at the nominal tolerance:
  - (A) proceed as ruled. Section 5's ladder prunes inside the six on B2's
    own floor, in an order only that floor fixes.
    - It clears 0.90 in 306 of the 720
      possible orders (720 of 720 on the
      most lenient evaluation).
    - Otherwise B2 is `WEAK_POWER_OR_VACUITY` at floor build, before any
      candidate run, and returns to Max;
  - (B) gate five cells, dropping `earn_p50.older`: 0.926 / 0.972. B2 then does
    not certify the older cohort's median earnings level;
  - (C) gate four cells. Dropping both medians gives 0.964 / 0.988; dropping
    `earn_p50.older` and `earn_zero_rate.older` gives 0.956 / 0.984;
  - (D) keep the six and widen their tolerance to k = 3.26,
    1.06 times k = 3's: 0.901 / 0.956. The ladder
    stays as a backstop;
  - (E) keep B2 unadmitted. H and B3L stay blocked.

  More gate seeds, pooled cohorts and a correlation-aware critical value
  were considered and set aside (section 11).

  The decision aid is `trackb-ruled-power-20261011/OPTIONS.md` in the
  launch-evidence directory. It says, for each option, what B2 stops
  certifying and what H and B3L then cannot rely on, and gives each
  option's power at tolerances 15% below to 8% above nominal. It
  proposes (A) as the default: it is the ruling as made, and a ladder
  failure stops B2 at floor build, before any candidate outcome, so the
  choice among (B)-(D) can then use B2's real tolerances.

If a family's last cell may be pruned, these surfaces reach 0.90 on the
binding evaluation at the uncapped tolerance (the power record's
`decision_illustrations`). They are post-run figures for these
decisions and decide nothing:

| Basis | Largest surface at 0.90 | Its families | Most families at 0.90 |
|---|---|---|---|
| Household resampling, as measured | 6 cells, 0.952 | log quantiles, zero rate | 3 (autocorrelation, log quantiles, zero rate), 0.946 |
| Over-limit cells' sampling variance × d² (95th percentile) | 5 cells, 0.947 | log quantiles, zero rate | 3 (autocorrelation, log quantiles, zero rate), 0.940 |

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
- Import `copy_persons` from `scripts/track_b_b0_1_planning_values.py`
  for the scoring bootstrap, and test that the scorer and arm F build
  identical frames for the same multiplicities.
- **The root seed (Q6 round 2).** Arm F's `anchor_multiplicities` and arm
  D's `design_multiplicities` take no root argument. They read protocol
  v2's root, 20260930, from the module constant `BOOTSTRAP_ROOT_SEED`, and
  the planning script stays pinned. So B2's scorer does not call them.
  - It carries its own copies, whose only change is a `root` parameter
    passed explicitly on every call, worker processes included. B2 calls
    them with root 20261002 and streams [root, b, 0] and [root, b, 4].
  - A differential test checks that, with root 20260930, each copy returns
    the planning functions' multiplicities for replicates 0-99.
  - A second test checks that the scorer never reads
    `BOOTSTRAP_ROOT_SEED`.
- Implement section 7's stratum rule: merge one-cluster strata, and use
  exact Rao-Wu by integer copies at scale L. Test it on invented inputs,
  including a differential test that at L = 1 it equals arm D's
  multiplicities.
- Use t\*_m,ν with ν counted by the floor builder after the merges
  (section 7), and publish the strata counted by cluster count before any
  candidate run. If ν is 0, stop at floor build as
  `WEAK_POWER_OR_VACUITY`.
- Name the gated surface in the headline (d781): earnings levels and
  zero rates only, with H and B3L relying on B2 for levels only.
- Carry d1342 (option A). The floor builder runs section 5's ladder inside
  the six on B2's own floor until power reaches 0.90 with at least four
  cells. If it cannot, B2 stops at floor build, before any candidate
  outcome, and options B-D return to Max priced on B2's real
  tolerances.
- Cite B1 v2's pass (issue #42 comments 6110674288 and 6113379406) with
  its label, "reconstructed reproduction (weaker than bit-for-bit)"
  (d622).
- Launch the floor builder and any run not pinned to another environment
  with at most four BLAS and OpenMP threads and
  `OMP_WAIT_POLICY=PASSIVE`, as Max ruled on 2026-10-11 for the shared
  host. Candidate 3's projection loop is pinned to eight threads and
  `ACTIVE` by its frozen environment guard. If B2 needs it, the
  registration states that pin and why.
- A rescoped registration under d781 names the gated families in its
  headline and scores every other cell report-only.

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
- Section 16's design rule did not hold at the 2006 pseudo-origin, so
  the same question arises for every later gate's resampling.

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

It printed nothing from the 20 files on the audit's §15.4 list other
than:

- those two line ranges;
- one grep of `m6_projection_engine.md` that printed line numbers and
  three headings (lines 3689, 3709 and 3766).

Three of its searches before the freeze took in excluded files and
printed nothing from them: two file-name searches over the worktree and
one over `tests/*.py`. It opened no selection ledger, no codebook
frequency table and no PSID data before the freeze. It did not read the ledgers' 2006
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

**Pre-freeze design review.** Two in-session workflows of Opus 5.5
agents read the draft protocol and plan: 6 agents on 2026-09-30
(22:42-22:54 UTC) and 49 reviewers and verifiers on 2026-10-01
(02:07-02:44 UTC), each reviewer with one lens (rulings, power,
blindness, statistics or feasibility). Their findings shaped sections
4-9 and 16. None of them can serve as the Q6 reviewer. The reads record
below shows what they opened beyond the author's reads:

- `gates.yaml` lines 5324-5745 and `m6_projection_engine.md` lines
  3600-3800, outside every range the inventories flag in those files;
- the two codebook-evidence JSON files, through scripts that printed
  column names, row counts and how many code-map rows have a populated
  frequency, and no frequency, percent or label;
- tool-output files and the workflow journal in this session's own
  transcript subfolder.

Eleven of their recursive or glob searches took in excluded files:

- five printed nothing from them;
- five printed only file names and match counts;
- one returned nothing before its workflow was stopped.

Two of the five that printed names or counts were `git grep` calls on
`HEAD`. Their output lines start with the revision, so the first version
of the extractor's line counter missed them and counted zero. Q6 round 2
found this, and the counter now tests the field after a revision too.
They printed only the names, and the counts, of files holding the
codebook tokens.

Their other mentions of excluded files are exclusion pathspecs, line
counts and mechanical scans.

**After the freeze.** The session launched the run and watched its
progress log, which prints stage names and replicate counts only. It
never opened the checkpoint, which the script deleted. When the run
ended it read the planning-value record, ran the power script on it, and
read the power record. It computed d781's and d782's figures from the
planning record alone, and corrected audit §11's "upper bound" wording
from section 10's r. Apart from the run itself, it opened no PSID file,
selection ledger, §15.4 file or codebook table after the freeze. It did
not read its own transcript folder again; the reads record below comes
from the app's transcript export.

**The reads record.** `docs/design/track_b_b0_1_addendum_reads.json`
is written by `scripts/track_b_b0_1_addendum_reads.py` from this
session's transcript export, taken after Q6 round 1. It lists every
tool call of the session and its agents up to the export, 1,801 calls:
the paths, ranges and patterns each named, and each shell command's
first line, SHA-256 and named paths.

It flags the 105 calls that name a restricted or excluded path, or
whose recursive grep, `git grep` or glob covers one, and classifies
each. None is left unresolved, and seven are classified by hand with a
note. For each flagged call it keeps the full command. Where a call's
scope covers an excluded file, it also counts the output lines that
begin with an excluded path, and records only that count. It holds no
other tool output. Python code that walks the tree is not parsed; such
code is flagged only when it names an excluded path.

Calls after the export, including the round-2 dispatch, are in
section 15.

**The 2026-10-11 revision.** A second Claude Code session (Opus 5.5), the
Track B forward-earnings session, wrote the changes after Max's rulings.
It shares no context with the author above.

Before opening any other file it read:

- `RESTRICTED-FILES.md`;
- the audit's §15.4 exclusion list.

It then read:

- this addendum, the round-1 review and the planning, power and reads
  records;
- the power, tables, reads and planning-value scripts (the last only
  around arm D's `design_multiplicities`), the record tests and
  `tests/conftest.py`;
- the decision log's d765, d781 and d782 entries;
- for B1: `track_b/` and the candidate-3 runner's environment guard;
- the candidate-3 artifact's top-level keys, `provenance`,
  `runtime_identity` and `dependency_snapshot`, and its sidecar;
- the Track B design, through one grep that printed the lines naming
  months, births and H.

It opened no file on the §15.4 list, no selection ledger, no codebook
table and no PSID file. Its only computation on data was the ruled power,
from the planning record.

Calls that took in excluded files, each mechanically:

- five `pytest --collect-only -q -m <tier>` runs over the suite, which
  import every test module and print one count each;
- `git diff --stat` and `--name-status` listings;
- one rerun of the reads extractor on the round-1 export. The session did
  not open the export (section 15);
- the exposure inventory, rerun at each review head from round 2 on, which
  reads every tracked file's bytes and records only line ranges, pattern
  families and counts;
- the review-root builder, run for each round from 2 on, which extracts
  the head, removes the denied files unread and scans the rest only for
  the two codebook tokens.

Further reads and actions of this session, recorded here in prose. No
transcript-derived record exists for this session; only the first
author's reads have one.

- **B1 v2.** This session froze, registered and launched the B1 v2 run,
  and published its result.
  - It wrote both issue #42 comments: the registration, 6110674288, and
    the result, 6113379406. It read no other #42 comment.
  - It built B1's pinned environment and probed it without data.
  - It never opened B1's raw output, its evidence files or its sealed
    logs. It listed the output directory's file names and counted them,
    listed the sealed directory's file sizes, and read each file's
    modification time.
  - Every B1 figure in this addendum comes from the frozen summarizer's
    value-free summary, which reports statuses, counts and hashes only.
  - The candidate-3 artifact fields it read are those listed above. Its
    `provenance` holds row counts for M6's boundary-2014 run: the source
    rows, the anchor's person count and the 2015-2019 truth rows. It
    holds no earnings level, gap or floor.
- **d1342.** This session drafted d1342's decision aid
  (`trackb-ruled-power-20261011/OPTIONS.md` in the launch-evidence
  directory).
  - It had two GPT-6.1 Sol reviews of the ruled power and the aid, each on
    a narrow root: the planning and power records, the power scripts and
    tests, this addendum, the rulings and the aid.
  - B1's freeze had five Sol reviews, on roots holding B1's code, its
    registration and the candidate-3 artifact and sidecar.
  - No root held a file on the §15.4 list.
- **The B2 build.** This session briefed an Opus build lane to write B2's
  floor builder, comparator and scorer in a standalone clone. Its tests
  use invented data only. The brief forbids running any of it on PSID and
  reading any §15.4 file or selection ledger.

## 15. The blinded review (Q6)

The plan was fixed before the first review. Its read-log rule was
sharpened after round 1 (below).

- **Root.** `git archive` of the PR head into a new directory that is
  not a git repository and is outside every restricted folder. Removed
  whole: the 20 files of audit §15.4; every further file the exposure
  inventory flags when rerun at the PR head; and
  `data/external/psid_codebook_field_evidence/`, whose code maps carry
  frequency columns for B2's 2012 and 2014 labor-income variables. The
  builder also removes every other file that names both a code map and
  frequencies, and refuses the root if one remains. A file this pull
  request adds or changes may be kept by name when it only names the
  tokens (the builder, its test and the reads record do); the root
  record lists each one.
- **Context copies.** Five named files are copied in, each hashed and
  scanned with the inventory's patterns: the Track B design, the d693
  `RECOMMENDATION.md`, PR #490's two review comments, and the d693 and
  d622 ruling texts. They are the only launch-evidence material in the
  root. They are a deliberate exception to the Q6 rider's exclusion of
  the launch-evidence directory. From round 2 the root also holds the
  d765, d781 and d782 ruling texts and d1342's decision aid, nine copies
  in all; from round 4 it also holds the d1342 ruling text, ten in all.
- **Lane.** `subfleet run --task review -m opus -I -s read-only -D
  <root>`: Read, Glob and Grep only.
- **Read log.** `scripts/track_b_b0_1_review_root.py readlog` extracts
  from the lane's transcript every path a tool call names and every path
  a Glob or Grep result returns. A review in which any of them lies
  outside the root, or on a denied path, does not count, and a new one
  is dispatched. Paths quoted inside a file the lane read are content,
  not reads. When the harness saves an oversized result outside the
  root, the log records the notice, and the review is void only if a
  later call opens that file.
  - Since Q6 round 6, the log also checks each Glob pattern and each
    Grep file filter. One that is absolute, holds a `..` segment, or
    names a denied path voids the review, even if it only confirms the
    path's absence.
  - Since Q6 round 7, a pattern also names a denied path when one of its
    segments is the path's basename, or its stem followed by a dot, and
    names the codebook directory when a segment is its last one. A
    wildcard fragment of a name, such as `*name_part*`, is not
    classified; the review prompt forbids it.
  - Since Q6 round 8, the log expands a pattern's brace groups first, so
    a name split across a group, such as `{stem,x}.md`, is read whole.
    A pattern with more than 4,096 alternatives is not classified, and
    voids the review; since PR #534 so is one longer than 1,024
    characters, past the read log's work limits or with a class of more
    than 1,024 characters.
  - Since Q6 round 9, a segment that holds a denied name's whole stem
    and, read as a wildcard, matches that name also names it: `stem*`,
    `stem?md`, `stem[.]md`. An unbalanced brace is literal text, and the
    scan goes on after it. Only a wildcard that holds part of a stem
    stays unclassified.
  - Since the follow-up to Q6 round 10 (PR #534), a pattern is also read
    as ripgrep, Node and Bun read it (a bracket class is one character
    whatever it holds, as in `stem[.,]md`; a brace group without a comma
    stands for its content; brace sequences, escapes, Node's backslash
    separators, extglobs and POSIX classes are resolved; case is
    ignored), a segment that matches a denied name and reads no other
    character at any position of its stem names it, a pattern holding
    `!(...)` that names no denied path is not classified, and the denied
    names are every file the root record removed, the codebook files and
    code-map tables included.
  - Each log's schema version records the rule it was made under. The
    rule as it now stands is `track_b_b0_1_review_read_log.v7`.
  - It also checks returned paths given relative to the root, as the
    harness returns them.
  - Rounds 5-10's logs were regenerated under the rule as it now stands.
    Round 1's log came from another session's transcript, under the rule
    as it stood then, and is not regenerated.
- **Numbers.** Numerical reproduction is in the CI-pinned tests, not the
  reviewer's job.

**Round 1: request changes.**

- **Root.** `git archive` of `5813d8f`, 1,709 files, manifest SHA-256
  `9dad8761a38c19c0…`. The builder removed 26 files: 20 excluded files
  whole, the six files of the codebook folder, and three other files
  that name both tokens. It kept the three files of this pull request
  that only name them. It added the five context copies.
  `docs/design/track_b_b0_1_addendum_q6_root_r1.json` is the root
  record.
- **Lane.** Subfleet job `20261001-115147-b01-addendum-q6`: Opus 5.5 in
  isolated-review mode, with Read, Glob and Grep only, no MCP servers,
  plan permission mode and the root as its only directory. It ran on
  2026-10-01 from 16:50 to 17:05 UTC.
- **Read log.** `docs/design/track_b_b0_1_addendum_q6_readlog_r1.json`:
  69 tool calls (42 Read, 25 Grep, 2 Glob). All 27 paths they named or
  returned lie inside the root, and none is denied. Two Grep results
  were too large, and the harness saved them in the lane's own project
  folder; the lane did not open them. The first version of the read log
  also counted every absolute path quoted in a result, including paths
  quoted in the files under review, and so flagged paths the lane never
  touched. The rule above replaced it. The review counts.
- **Verdict.** `REQUEST CHANGES`, with no high finding, three medium and
  seven low. The review is
  `docs/design/track_b_b0_1_addendum_q6_review_r1.md`. It met no B2
  outcome and confirmed that the script matches the protocol, that
  nothing the run read or recorded is dated after 2010, and that the
  verdict follows from the records.

| Finding | Disposition |
|---|---|
| M1: d781 framed toward (a) and left out amending Q2 | Section 11 restates the flip; d781 lists its options in no order and adds (d), with figures from the power record; d781's decision record carries a note |
| M2: the design ratio's own sampling uncertainty, and the critical value under design clusters | Section 10's limits and d782 state both; a registration under d782 (a) uses the t value |
| M3: section 14's claim, and the reads record's blindness to recursive and glob reads | The extractor flags recursive and glob scopes that cover an excluded path, counts output lines that begin with one, and keeps every flagged call's full command. Section 14 is restated from the regenerated record |
| L1: the audit's "upper bounds" were corrected in one place only | Audit sections 1, 11, 11.2, 11.4 and Q2 now call them reference points |
| L2: the uncapped tolerance is nominal, not a bound | Section 11 says so and gives the verdict at 5% and 10% wider tolerances |
| L3: the outcome-blind flags are constants | Section 10 says so and names the evidence |
| L4: B2's seeds were unnamed | Section 7 names them |
| L5: the half-sample evidence had no provenance | Section 13 gives the check's command, time and script state |
| L6: the Monte Carlo threshold | Section 11 gives the measured 2.34 |
| L7: a guard refusal in a worker would resume | Section 10 notes it |

**Round-1 findings, rechecked 2026-10-11.** Each disposition above is in
place at this head:

- **M1.** Section 13 lists d781's options in no order, with (d) and its
  figures. d781 has since been ruled (section 2).
- **M2.** Section 10 states d's own sampling uncertainty. After d782,
  section 7 registers the rider: Student t with the design's ν degrees of
  freedom, 2.724 at m = 6 and ν = 63. Section 11's ruled power uses it.
- **M3.**
  - The extractor flags recursive and glob scopes that cover an excluded
    path (`Checker.scope`). It counts the output lines that begin with
    one, and keeps each flagged call's full command. Fourteen calls carry
    a scope flag: three of the author's and eleven of its agents'. Section 14 is restated from that record.
  - This revision corrected one leftover. The extractor's docstring and
    the record's `method` still said it reads no tool output, though it
    reads a flagged call's output to count lines. Both now say what it
    does.
  - The record was regenerated from the same export, whose SHA-256 is in
    its `source`. The first regeneration changed only `method`, and
    `restricted_entries_checked`, which went from 110 to 114 for the
    entries `RESTRICTED-FILES.md` had gained.
  - Q6 round 2 then found that the line counter missed `git grep`
    output prefixed with a revision (`HEAD:path`). The counter now tests
    the field after the first colon as well, and a test pins it. The
    second regeneration moved two agent calls (`git grep -c` and
    `git grep -l` on `HEAD`) from "printed nothing" to "printed names or
    counts only". Section 14 is restated to match. No other call, flag or
    class changed.
- **L1-L7.** Audit sections 1, 11, 11.2, 11.4 and Q2 call the standard
  errors reference points (L1). The rest are in place:
  - L2: section 11 calls the tolerance nominal;
  - L3: section 10 says the outcome-blind flags are constants;
  - L4: section 7 names the seeds;
  - L5: section 13 gives the leak check's command and time;
  - L6: section 11 gives the 2.34 threshold;
  - L7: section 10 notes the worker quirk.

**Round 2: request changes.**

- **What changed in the form.** Three changes from round 1, each made
  before the round-2 dispatch:
  - **The lane.** Round 2 ran on GPT-6.1 Sol, Max's default reviewer since
    2026-10-09, through `subfleet run --task review --tier hard -I -s
    read-only -D <root>`. The Opus lanes were mostly closed that day.
  - **The read log.** A Codex lane's tools are shell commands, so its
    read log comes from `review_root.py readlog --format codex`. Every
    command word that leaves the root voids the review: an absolute path
    outside it, a home path, a `..` segment, or (after this round) an
    unquoted shell expansion.
  - **The context copies.** There are nine.
    - The design and the d693 `RECOMMENDATION.md` are byte-identical to
      round 1's copies.
    - PR #490's two comments and the d693 and d622 ruling texts were
      rebuilt from GitHub and the decision log, because round 1's copies
      sat in another session's scratchpad.
    - New: the d765, d781 and d782 ruling texts and d1342's decision aid.
- **Root.** `git archive` of `0cae9a7`, 1,858 files, manifest
  SHA-256 `7595bb54d52e6487…`.
  - The builder removed 27 files whole: the union of the
    three exposure inventories' exclusions (21 files,
    including `tests/harness/test_epuf_gate.py`, new from the master
    merge) and the six files of the codebook folder.
  - It removed 4 other files that name both
    tokens, and kept the three files of this pull request that only name
    them.
  - The root record is `docs/design/track_b_b0_1_addendum_q6_root_r2.json`.
- **Lane.** Subfleet job `20261011-085345-b01-addendum-q6-r2`, read-only
  and isolated, with the root as its working directory. It ran on
  2026-10-11 from 12:53 to 13:16 UTC. Subfleet records GPT-6.1 Sol as
  requested. It could not attest the served model, because an isolated
  ephemeral Codex run persists none.
- **Read log.** `docs/design/track_b_b0_1_addendum_q6_readlog_r2.json`
  covers 39 commands. None names a path outside the root, a denied path or
  an unquoted shell expansion, so the review counts. The review's prose
  mentions delegated work, but the lane's event stream shows no sub-agent
  events. The log covers the commands the stream records.
- **Verdict.** `REQUEST CHANGES`, with no high finding, three medium and
  three low. The review is
  `docs/design/track_b_b0_1_addendum_q6_review_r2.md`. It met no B2
  outcome and no 2008/2010 selector outcome. It confirmed:
  - the ruling quotations and the M2 rider;
  - section 11's verdict and figures;
  - the section-16 protocol block's pinned hash.

| Finding | Disposition |
|---|---|
| M: a stratum with three or more clusters would be resampled by the ordinary bootstrap, not Rao-Wu | Section 7 admits only two-cluster strata. B2's floor builder stops before any candidate run if any stratum has one cluster or three or more (sections 7, 9, 13). (Superseded by round 5's L3: the stratum rule is now fixed in section 7.) |
| M: the reads extractor missed `git grep` output prefixed with a revision | The counter tests the field after a revision too, and a test pins it. The record was regenerated: two agent calls moved to "names or counts only". Section 14 and this section are restated |
| M: the Codex read log approved a path built from `$PWD` | The read log voids any unquoted shell expansion. Tests cover `$NAME`, `$Ellipsis`, `$(...)` and backquotes, and allow single-quoted dollars. Under the fixed rule this round's log still counts |
| L: "thirteen" scope-flagged calls; the record has fourteen | Corrected and pinned |
| L: section 15 described round 1's lane and context only | This record states round 2's form |
| L: the root-seed handoff had no executable interface | "To B2" specifies root-parameterised copies, with a differential test against the pinned functions |

**Round 3: request changes.**

- **Root.** `git archive` of `2436954`, 1,861 files, manifest SHA-256
  `b7d56a057e35c5e1…`, built in round 2's form.
  - The exposure inventory was rerun at that head, to a file outside the
    worktree. It flagged no file beyond round 2's 20. It is committed as
    `docs/design/track_b_b0_1_addendum_q6_inventory_r3.json`.
  - The builder removed the same 27 files whole and the same four
    code-map tables.
  - The root record is `docs/design/track_b_b0_1_addendum_q6_root_r3.json`.
- **Lane.** Subfleet job `20261011-092342-b01-addendum-q6-r3`, GPT-6.1 Sol
  as requested (unattested, as in round 2), read-only and isolated. It ran
  on 2026-10-11 from 13:26 to 13:48 UTC.
- **Read log.** `docs/design/track_b_b0_1_addendum_q6_readlog_r3.json`
  covers 30 commands, none leaving the root, so the review counts.
  - It was extracted with the read log as fixed after this round (below).
  - Round 2's log, rechecked under the same rule, is unchanged.
  - One command of round 3's ran Python code that held invented `$X`
    strings to test the read log. Under the fixed rule, code for a
    non-shell interpreter is not a shell script, so they are not
    expansions.
- **Verdict.** `REQUEST CHANGES`, with no high finding, one medium and one
  low. The review is `docs/design/track_b_b0_1_addendum_q6_review_r3.md`.
  It found every round-2 finding resolved except the expansion gap. It
  met no B2 outcome and no 2008/2010 selector outcome.

| Finding | Disposition |
|---|---|
| M: a nested `sh -c '...'`, brace expansion or ANSI-C quoting could escape the Codex read log | The read log rescans every shell script at every depth: a shell's `-c` argument and `eval`'s words. It treats `$'...'` and `$"..."` as expansions, and splits brace expansion into its parts. Code for other interpreters is scanned for paths only. Tests cover each case, and five mutants each fail them. The log's docstring says it is a detector, not a sandbox |
| L: element 8 said to import `design_multiplicities`, which reads protocol v2's root | Element 8 points to section 13's root-parameterised copies |

**After round 3: d1342.** Max ruled d1342 on 2026-10-11 (option A, proceed
as ruled), and sections 1, 2, 5, 11 and 13 record it.

**Round 4: request changes.**

- **Root.** `git archive` of `71961b9`, 1,866 files, manifest SHA-256
  `73a1a9d86ebeacd3…`.
  - The inventory rerun is
    `docs/design/track_b_b0_1_addendum_q6_inventory_r4.json`. It flagged
    nothing new.
  - The same 27 files and four tables were removed. Ten context copies
    went in: round 2's nine and the d1342 ruling.
  - The root record is `docs/design/track_b_b0_1_addendum_q6_root_r4.json`.
- **Lane.** Subfleet job `20261011-113615-b01-addendum-q6-r4`, GPT-6.1 Sol
  as requested (unattested), read-only and isolated. It ran on 2026-10-11
  from 16:12 to 16:23 UTC.
- **Read log.** `docs/design/track_b_b0_1_addendum_q6_readlog_r4.json`
  covers 13 commands, none leaving the root.
- **Verdict.** `REQUEST CHANGES`, with no high finding, one medium and no
  low. The review is `docs/design/track_b_b0_1_addendum_q6_review_r4.md`.
  It confirmed:
  - d1342 is carried exactly;
  - element 8 is resolved;
  - the record is complete at the rule level.

| Finding | Disposition |
|---|---|
| M: five more ways a logged command could leave the root while the review counted: a tab-separated word, `bash -o errexit -c`, `~user` and zsh's `=program`, `cd`, and an executable path used as an operand | Each is closed. Words are re-split at any whitespace. Every word after a shell program is a script. A `~` shell word and `=program` void the review, and so do `cd`, `pushd` and `popd`. Executables are exempt only in program position. The log's docstring now calls it a conservative detector that cannot certify a shell lane. Tests cover each case, and six mutants each fail them. The read logs of rounds 2-4 were regenerated with the fixed tool, and each still counts |

**The Q6 form, corrected after round 4.** d693's Q6 rider asks for "an
independent Opus lane in Subfleet's isolated-review mode on a cleaned
root, with no shell and no web".

- Round 1 had that form. Rounds 2-4 ran on GPT-6.1 Sol, the default
  reviewer since 2026-10-09, and that lane has a shell.
- Their read logs show no command leaving the root. But a shell lane's
  log cannot certify it blind, because a program can build a path at run
  time.
- So rounds 2-4 count as additional independent reviews, which shaped
  the fixes above, not as the Q6 review of record.

**Round 5** was dispatched as the Q6 review of record, in round 1's
form: Opus 5.5 in isolated-review mode, with Read, Glob and Grep only, no
MCP servers, plan permission mode, the root as its only directory, and
the Claude read log.
A first dispatch, job `20261011-163220-b01-addendum-q6-r5`, was cancelled
about a minute after launch so that master could be merged first. Its
transcript holds only the session's start event and no tool call. Round 5
reviews the head after that merge.

**Round 5 (void as the Q6 review of record under the rule fixed after
round 6): request changes.**

- **Root.** `git archive` of `046480a`, 1,934 files, manifest
  SHA-256 `5098b02ca4cfb2fa…`.
  - The inventory rerun is
    `docs/design/track_b_b0_1_addendum_q6_inventory_r5.json`. It flagged
    nothing new.
  - The same 27 files were removed whole, and four
    code-map tables. The ten context copies went in.
  - The root record is `docs/design/track_b_b0_1_addendum_q6_root_r5.json`.
- **Lane.** Subfleet job `20261011-164355-b01-addendum-q6-r5b`, on Opus 5.5
  in isolated-review mode with Read, Glob and Grep only, plan permission
  mode and the root as its only directory. It ran on 2026-10-11 from
  20:47 to 20:56 UTC and exited 0.
  - Subfleet then marked the job lost, because a process of the lane
    lingered after the exit receipt, and it exported no deliverable.
  - The review below is the result event of the lane's own stream-json
    transcript, copied verbatim.
- **Read log.** `docs/design/track_b_b0_1_addendum_q6_readlog_r5.json`,
  from that transcript, covers 45 tool calls. Every path named or
  returned lies inside the root, and no oversized result was saved
  outside it.
  - One Glob's pattern names denied paths: an absence check that
    returned nothing. The first log missed it, because it did not
    classify patterns; Q6 round 6 found the gap.
  - Under the rule as fixed after round 6, which voids a review whose
    calls name a denied path, round 5 does not count as the Q6 review of
    record. Its findings were answered all the same.
- **Verdict.** `REQUEST CHANGES`, with no high finding, one medium and five
  low. The review is `docs/design/track_b_b0_1_addendum_q6_review_r5.md`.
  - It met no B2 outcome and no 2008/2010 selector outcome.
  - It checked every figure in section 11's ruled subsection by hand.
  - It found the rulings carried exactly, and the protocol block pinned
    and last in the file.

| Finding | Disposition |
|---|---|
| M1: section 14 omitted this session's #42 comments, its part in B1's run, whether it opened B1's output, d1342's aid and its reviews, and that its reads have no extractor record | Section 14 adds each, and states that no B1 output, evidence file or sealed log was opened |
| L1: "only the most lenient" sat beside household resampling's 0.952 | Both sentences now say "of the evaluations on the ruled configuration (household resampling, d781's basis, excepted)" |
| L2: the t value's authority was cited only to the round-1 rider | Section 2 adds that d1342's question named "t at 63 df" and Max ruled A on that configuration |
| L3: the stratum fallback was left to an amendment after the floor | Section 7 fixes it now: one-cluster strata merge into the nearest stratum code; strata with three or more clusters get exact Rao-Wu by integer copies at scale L; ν is counted after the merges. Sections 9 and 13 follow |
| L4: stale wording on the ladder's floor and on the context copies | Both are corrected |
| L5: "nothing after 2010 was recorded" | Section 10 names the 2012/2014 support counts the record copies from the frozen audit record |

**Round 6: request changes.**

- **Root.** `git archive` of `0487adc`, 1,938 files, manifest SHA-256
  `13c185da7f233ab4…`.
  - The inventory rerun is
    `docs/design/track_b_b0_1_addendum_q6_inventory_r6.json`. It flagged
    nothing new.
  - The same 27 files were removed whole, and four code-map tables. The
    ten context copies went in.
  - The root record is `docs/design/track_b_b0_1_addendum_q6_root_r6.json`.
- **Lane.** Subfleet job `20261011-170343-b01-addendum-q6-r6`, in round 5's
  form (Opus 5.5, isolated review, Read, Glob and Grep only). It ran on
  2026-10-11 from 21:13 to 21:22 UTC and exited 0.
  - As in round 5, Subfleet then marked the job lost because a lane
    process lingered, so the review is the result event of the lane's
    transcript, copied verbatim.
- **Read log.** `docs/design/track_b_b0_1_addendum_q6_readlog_r6.json`,
  under the fixed rule, covers 37 tool calls.
  - Every path named or returned, the relative result paths included, lies
    inside the root.
  - No pattern is absolute, leaves the root or names a denied path.
  - So round 6 counts. It is the first Q6 review of record under the rule
    as fixed.
- **Verdict.** `REQUEST CHANGES`, with no high finding, one medium and
  three low. The review is
  `docs/design/track_b_b0_1_addendum_q6_review_r6.md`.
  - It met no B2 outcome and no 2008/2010 selector outcome.
  - It checked each of round 5's dispositions in substance, and section
    11's figures.

| Finding | Disposition |
|---|---|
| M1: the Claude read log classified neither Glob patterns nor results given relative to the root, so round 5's Glob naming denied paths went unflagged | The read log classifies Glob patterns and Grep file filters: absolute, `..` or denied-name patterns void the review. It takes relative result lines as paths. Tests cover each case, and four mutants fail them. Rounds 5 and 6's logs were regenerated, round 5 no longer counts, and this section and the plan's read-log rule say so |
| L1: element 8 gave arm D's rule and the stratum rule side by side | Element 8 applies arm D's rule to two-cluster strata only; other strata follow the stratum rule. Round 2's row is marked superseded |
| L2: the one-cluster merge was ambiguous when such strata are adjacent | They merge into the nearest stratum with two or more clusters, the lower code on a tie. If there is none, all merge into one. Merges apply together, then the strata are counted |
| L3: section 14 omitted the inventory reruns and root builds | Section 14 lists both |

**Round 7: approve.**

- **Root.** `git archive` of `05dbd5b`, 1,942 files, manifest SHA-256
  `a999c4d27cf77146…`.
  - The inventory rerun is
    `docs/design/track_b_b0_1_addendum_q6_inventory_r7.json`. It flagged
    nothing new.
  - The same 27 files were removed whole, and four code-map tables. The
    ten context copies went in.
  - The root record is `docs/design/track_b_b0_1_addendum_q6_root_r7.json`.
- **Lane.** Subfleet job `20261011-173633-b01-addendum-q6-r7`, in round 6's
  form, served by Opus 5.5. It ran on 2026-10-11 from 21:40 to 21:48 UTC
  and exited 0. Its prompt added that no pattern or file filter may name
  a file expected to be absent, even to confirm that it is.
- **Read log.** `docs/design/track_b_b0_1_addendum_q6_readlog_r7.json`
  covers 32 tool calls. Every path named or returned lies inside the
  root, and no pattern is absolute, leaves the root or names a denied
  path, under the rule as tightened after this round. Round 7 counts.
- **Verdict.** `APPROVE`, with no high or medium finding and three low.
  The review is `docs/design/track_b_b0_1_addendum_q6_review_r7.md`.
  - It met no B2 outcome and no 2008/2010 selector outcome.
  - It checked each of round 6's dispositions in substance, section 11's
    figures against the record, and the rulings' quotations against the
    ruling texts.

| Finding | Disposition |
|---|---|
| L1: the read log flagged a denied file only when a pattern held its full path, not its basename | A segment equal to a denied basename, or to its stem followed by a dot, or to the codebook directory's last segment, now voids the review. Tests cover a nested denied file by basename and by stem, and the codebook directory; four mutants fail them. Wildcard fragments stay unclassified, and the plan's rule says so. Rounds 5-7's logs were regenerated: round 5 stays void, rounds 6 and 7 count |
| L2: element 8 kept "only two-cluster strata are admitted" and "a stratum with one cluster adds nothing", against its own stratum rule | The heading now says arm D's rule is Rao-Wu only for two-cluster strata. ν is counted after the merges, where a merged one-cluster stratum adds one. `design_degrees_of_freedom` follows the same reading and raises when ν would be 0; two mutants fail its test. The 2006 record had no one-cluster stratum, so ν there stays 63 and no figure moves. The review's edge case, ν = 0 after the merges, now stops B2 at floor build |
| L3: the context-copy sentence read as if round 2 held the d1342 ruling | Round 2 held nine copies; the d1342 ruling went in from round 4, making ten |

Round 7 approved `05dbd5b`, and these fixes changed the head after it.
Round 8 confirms them.

**Round 8: approve.**

- **Root.** `git archive` of `1e4d226`, 1,946 files, manifest SHA-256
  `73c0d9c2f409eaaa…`.
  - The inventory rerun is
    `docs/design/track_b_b0_1_addendum_q6_inventory_r8.json`. It flagged
    nothing new.
  - The same 27 files were removed whole, and four code-map tables. The
    ten context copies went in.
  - The root record is `docs/design/track_b_b0_1_addendum_q6_root_r8.json`.
- **Lane.** Subfleet job `20261011-175818-b01-addendum-q6-r8`, in round 7's
  form, served by Opus 5.5. It ran on 2026-10-11 from 22:11 to 22:14 UTC
  and exited 0. Its prompt named the files changed since round 7 and asked
  four questions: whether each round-7 finding is resolved in substance,
  whether the changes bring a new problem, whether they touch the protocol
  block or blindness, and whether section 15's round-7 record matches its
  records.
- **Read log.** `docs/design/track_b_b0_1_addendum_q6_readlog_r8.json`
  covers 22 tool calls. Every path named or returned lies inside the
  root, and no pattern is absolute, leaves the root or names a denied
  path, under the rule as tightened after this round. Round 8 counts.
- **Verdict.** `APPROVE`, with no high or medium finding and two low.
  The review is `docs/design/track_b_b0_1_addendum_q6_review_r8.md`.
  - It met no B2 outcome and no 2008/2010 selector outcome.
  - It found each of round 7's three findings fixed in substance, the
    ν = 0 rule correct and no figure on the 2006 record moved.

| Finding | Disposition |
|---|---|
| L1: the read log missed a denied file named by its stem inside braces, with the extension outside them | `pattern_kind` expands brace groups before it classifies, nested groups included, and still cuts the pattern as written at its braces. Property tests check that a denied name cut into a brace group at any two points is flagged, that a pattern naming nothing denied is not, and that the classifier flags whatever round 7's rule flagged. Six mutants fail them. Rounds 5-8's logs were regenerated: round 5 stays void, rounds 6-8 count |
| L2: section 5 did not list the ν = 0 trigger for `WEAK_POWER_OR_VACUITY` | Section 5's rule, section 9's step 4 and the "To B2" list now name it |

Its observation, that the log lists Grep's context-line prefixes as
paths inside the root, is left as it is: it adds entries and hides none.

Round 8 approved `1e4d226`, and these fixes changed the head after it.
Round 9 confirms them.

**Round 9: approve.**

- **Root.** `git archive` of `266dd96`, 1,950 files, manifest SHA-256
  `103a6f11174bef67…`.
  - The inventory rerun is
    `docs/design/track_b_b0_1_addendum_q6_inventory_r9.json`. It flagged
    nothing new.
  - The same 27 files were removed whole, and four code-map tables. The
    ten context copies went in.
  - The root record is `docs/design/track_b_b0_1_addendum_q6_root_r9.json`.
- **Lane.** Subfleet job `20261011-185659-b01-addendum-q6-r9`, in round 8's
  form. Its transcript records Opus 5.5 and the tools Glob, Grep and
  Read. It ran on 2026-10-11 from 22:59 to 23:04 UTC and exited 0.
  - As in rounds 5 and 6, Subfleet then marked the job lost because a
    lane process lingered, so the review is the result event of the
    lane's transcript, copied verbatim.
  - Its prompt named the files changed since round 8, asked round 8's
    four questions of them, and asked of each finding whether it bears on
    the frozen record or only on the review tooling.
- **Read log.** `docs/design/track_b_b0_1_addendum_q6_readlog_r9.json`
  covers 20 tool calls. Every path named or returned lies inside the
  root, and no pattern is absolute, leaves the root or names a denied
  path, under the rule as tightened after this round. Round 9 counts.
- **Verdict.** `APPROVE`, with no high or medium finding and two low.
  The review is `docs/design/track_b_b0_1_addendum_q6_review_r9.md`.
  - It met no B2 outcome and no 2008/2010 selector outcome.
  - It found the B2 record sound and both of round 8's findings fixed in
    substance. It marks both of its own findings as bearing on the review
    tooling only.

| Finding | Disposition |
|---|---|
| L1 (tooling): an unbalanced `{` before a brace group stopped that group from being expanded | `brace_expansions` keeps an unbalanced brace as literal text and scans on, and every alternative is cut at any brace or comma left in it. A property test puts unbalanced braces and commas before a group that splits a denied name |
| L2 (tooling): a whole denied stem followed by a wildcard instead of a dot still passed | A segment that holds a denied name's whole stem and matches the name as a wildcard is now denied. A property test replaces the extension, or any of its characters, with wildcards. Four mutants fail the two fixes' tests. The plan's rule names the forms caught and the one left out |
| Observation: the log's schema stayed v5 across round 8's fix | The schema became v6 for the rule as it then stood, and the plan says a log's version records its rule. Rounds 5-9's logs were regenerated as v6: round 5 stays void, rounds 6-9 count |
| Observation: rescoping cannot cure ν = 0 | Section 5 says the decision queued there is how the critical value is set |

Round 9 approved `266dd96`, and these fixes changed the head after it.
Round 10 confirms them.

**Round 10: approve.**

- **Root.** `git archive` of `1aa179e`, 1,954 files, manifest SHA-256
  `f18f52572c4a5ae4…`.
  - The inventory rerun is
    `docs/design/track_b_b0_1_addendum_q6_inventory_r10.json`. It flagged
    nothing new.
  - The same 27 files were removed whole, and four code-map tables. The
    ten context copies went in.
  - The root record is
    `docs/design/track_b_b0_1_addendum_q6_root_r10.json`.
- **Lane.** Subfleet job `20261011-191406-b01-addendum-q6-r10`, in round
  9's form. Its transcript records Opus 5.5 and the tools Glob, Grep and
  Read. It ran on 2026-10-12 from 02:03 to 02:06 UTC and exited 0.
- **Read log.** `docs/design/track_b_b0_1_addendum_q6_readlog_r10.json`
  (made as v6, regenerated as v7) covers 21 tool calls. Every path named
  or returned lies inside the root, and no pattern is absolute, leaves
  the root or names a denied path. Round 10 counts.
- **Verdict.** `APPROVE`, with no high or medium finding and one low,
  which bears on the review tooling only and which the review says should
  not hold the merge. The review is
  `docs/design/track_b_b0_1_addendum_q6_review_r10.md`.
  - It met no B2 outcome and no 2008/2010 selector outcome.
  - It found round 9's findings and observations resolved, and the B2
    record unchanged in everything it registers on.

| Finding | Disposition |
|---|---|
| L1 (tooling): a character class holding a comma or a brace, such as `stem[.,]md`, hides a whole denied stem from the wildcard rule | Left for a follow-up change to the read-log tool, outside this addendum. No recorded round's pattern has a class of that shape. PR #534 is that change: a class is read whole, as the glob engines read it (v7, above). Rounds 5-10's logs, regenerated, keep their verdicts |
| Observation (tooling): the six codebook files are checked only through the codebook directory, not by their own basenames; the four removed code-map tables are not checked at all | The same follow-up passes every removed file to the read log. PR #534 fixes both: the read log's denied names are every file the root record removed, the six codebook files and the four code-map tables included |
| Observation (record): section 5 forbade only a rescoped registration before Max rules, which a registration changing how the critical value is set when ν is 0 might not be | Section 5 now says no rescoped or amended registration is written before he rules |

Rounds 7, 8, 9 and 10 each approved, and each counts. Round 10's head,
`1aa179e`, is the last one a Q6 review read. After it this addendum
gained only round 10's record, the one-word change to section 5 above,
and the merge of `master`. An independent review of that change precedes
the merge. After the merge, PR #534 changed only this section's read-log
text and its tooling rows (round 10's two, and the tense of round 9's
schema row).

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
