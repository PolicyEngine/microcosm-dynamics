# IC3 employer gate block — thresholds, partitions, and rulings

- **Design id**: `2026-07-17-ic3-employer-gate-block`
- **Status**: **DRAFT FOR REFEREE — NOT RATIFIED. Revision 3**,
  responding to the round-1 adversarial review of 2026-07-17
  (verdict: NOT RATIFIABLE AS DRAFTED — 5 blocking, 6 should-fix).
  Blocking items B1, B3, B4, B5 and should-fix S1 are addressed.
  **B2 remains open**: the refereed block YAML is still a required
  pre-lock artifact (§12.2a). The IC rename (#277) and its final
  design filename are now composed here, so that YAML must use
  `ic3` names from its first commit. §13 records every remaining
  decision and distinguishes a workstream decision from referee
  ratification. Nothing in this
  document binds until the lock ceremony flips it (§12). This document
  edits no `gates.yaml` cell, moves no threshold, builds no floor, and
  writes no test. Every number labelled PROPOSED is a proposal to the
  referee round, not a lock.
- **Plan**: issue #192 (E1–E12 battery, two-workstream split, protocol
  rules: disjoint calibration/gate cells, floors before thresholds, no
  one-shot candidate runs before IC3 locks).
- **Contracts**: ADR 0003 (`docs/adr/0003-employer-firm-extension.md`,
  IC1 spell schema and IC2 banding, **frozen**); ADR 0004
  (`docs/adr/0004-linkage-qc.md`, linkage QC). The three #224 adoption
  requirements are now in the ADR text on the exact composed head,
  not supplied by a comment-thread amendment.
- **Composed prerequisite record** (exact heads, all ancestors of this
  revision): master `691901f`; IC rename #277 `c5b4d11`; J2J/J2JOD
  references #228 `f5070b4`; ADR 0004 #224 `dff73d5`; cross-wave
  evidence #235 `c686f0f`; E4/E5 registered design #236 `73213c5`;
  byte-faithful seam anchor #274 `7411d8d`.
- **Intentionally not composed**: unfinished floor promotions #212 and
  #223. Their gate thresholds, builders, final filenames, and lock-time
  digests remain `PENDING`; this document must not pretend to consume
  them before their current heads are approved and merged.
- **Available evidence pins** (branch-composition pins, not lock-time
  merge ratification):

  | Source | Current path | SHA-256 | Lock-time merged pin |
  |---|---|---|---|
  | #228 E2 reference | `data/external/j2j_us_sexage_2015on.csv` | `6ca16b98b3e809ebf4493f6884c75bee712c727cce16ddc219e0fca97e7edf60` | PENDING merge |
  | #228 E11 reference | `data/external/j2jod_us_firmsize_od_2015on.csv` | `0f83df008ae498643b66ecf25187170014988f5fb1f761c84cf9882376e3bef6` | PENDING merge |
  | #235 cross-wave artifact | `runs/crosswave_jobid_check_draft_v0.json` | `33d4a7be88b417cb980ad4b12e65e1310eabd541a4926673e2414eead20941f1` | PENDING promotion/merge |
  | #235 builder | `scripts/build_crosswave_jobid_check.py` | `3887d392e3d978e2c5788e9e03557101129d9f759917037b756dba6e3ed0cb33` | PENDING merge |
  | #236 registered design | `docs/design/e4_e5_audit_manifest.md` | `d37b3ce014532e16e009cd5cf8b025601c029fd0bde48ac593c993d51025d103` | PENDING merge |
  | #274 seam anchor | `runs/seam_reconciliation_draft_v0.json` | `622ff4117a073c36698ed1e7d1828a6a0399471bfd0c06520e0da5ac2cd98e83` | PENDING promotion/merge |
  | #274 builder | `scripts/build_seam_reconciliation.py` | `61d9c99efcfdf2469caa5787499f853d0321128c56187553d5a5c87d69536f0f` | PENDING merge |
- **Authors**: joint Workstream A (@daphnehanse11) / Workstream B
  (@vahid-ahmadi) per the #192 interface-contract schedule (IC3 is the
  jointly-authored employer gate block).

## 1. Scope and shape of the block

This is the pre-registration draft for the `gates.employer` block
(E1–E12) that will be added to `gates.yaml` by amendment PR after the
referee round. It follows the repo's locked-gate schema conventions:
per-gate `thresholds` derived from committed floor artifacts as
`floor mean + k × floor sd` with machine-checkable derivations
(the `tests/test_gates_derivations.py` pattern), floor runs cited by
path, thin-cell exclusions pre-registered, and `locked: false` until
ratification.

Two structural rules carry over from #192 and ADR 0003 unchanged:

1. **Floors before thresholds.** Every gated cell cites a committed
   floor artifact; cells with no derivable floor cannot gate
   (consequences for E1-sector, E11-detail, E12 below).
2. **No one-shot candidate runs before IC3 locks.** Registration of
   employer-block candidates (issue #42 convention) opens only after
   the amendment PR merges with `locked: true`.

## 2. Proposed threshold policy (uniform, PROPOSED)

For every gated cell:

```
threshold_cell = max( floor_mean_cell + k × floor_sd_cell,
                      substantive_tolerance_gate )
```

- `k = 4` PROPOSED **as a policy choice, not as precedent-following**
  (corrects S1). The locked band is **1.8–8**, not 4.2–8: `gates.yaml`
  carries k = 4.2 (`:221`), 8 (`:297`), **1.8** (`:327`), **1.9**
  (`:333`) and 4 (`:493`), plus negative/band ks for minima and
  two-sided metrics. **Two locked ks sit below the proposed 4**, so
  precedent does not support 4 as conservative — it brackets it.
  The argument that does survive is the aggregated-sd one, and only
  partially: the B-side floors aggregate 24–36 year-pairs, but the
  SIPP-side floors aggregate 5 seeds *exactly as gate-1's did*, so
  for E3/E4/E5/E8/E9 there is no aggregation distinction from
  gate-1 at all and k = 4 is a bare policy choice against a band
  that reaches 1.8. Recorded as such. The referee round may set k
  per-gate; the Workstream A response of 2026-07-17 repeated the
  4.2–8 misquote and is corrected by the same edit (acknowledged
  2026-07-22).
- The `substantive_tolerance` term prevents degenerate-floor cells
  (several tenure quantile-gap floors and the E9-stay median floor are
  exactly 0.0 — see §4) from imposing a zero tolerance no model can
  meet; it is a per-gate scientific-relevance bound, every value
  PROPOSED in the table below.
- Cells flagged `thin` in the floor artifacts (E4/E5/E8/E9:
  `THIN_CELL_PERSONS = 200`; B-side: min denominator < 10,000 jobs)
  are report-only, pre-registered now.
- Verdict rule: a gated gate passes iff **all** its non-thin cells
  pass; report-only gates publish pass/fail per cell but do not block.

## 3. Per-gate proposals

Summary table (all numbers PROPOSED; "floor basis" names the committed
statistic the threshold derives from):

| Gate | Moment | Reference | Floor artifact | Recommended floor basis | First-lock status |
|---|---|---|---|---|---|
| E1 | employment share by firm-size band (× sector) | SUSB 2022 | #223 `e1` | SUSB noise-flag CV bounds + BDS YoY margin floor (coarsened `20_99`) | **report-only** — B1: every SUSB-derived margin is a deterministic function of a calibration target |
| E2 | hire/sep/J2J rates by sex × age | LEHD J2J `sa` (#228) | #223 PENDING; not composed here | ex-pandemic YoY \|log ratio\|, PENDING referee choice | **proposed gated** only after floor approval/merge |
| E3 | tenure quantiles by age | CPS tenure supplement 2020/22/24 | #212 `tenure_floors` | **ECDF max-gap** (heaping-robust) | **gated** |
| E4 | employer-retention pairs by age × sex | SIPP holdout | #212 `e4_retention_by_age_sex` | \|log rate ratio\| | **gated** (linkage-QC prerequisite, §9) |
| E5 | multi-window attachment runs by age | SIPP holdout | #212 `e5_runs_by_age` | \|log share ratio\| | **gated** (linkage-QC prerequisite, §9) |
| E6 | hire/sep flow rates by firm-size (× sector) | QWI | #223 `e6_e7` | ex-pandemic YoY \|log ratio\| | **report-only** — B1: the size margin is a linear functional of the calibrated size × sector cells |
| E7 | mean earnings (`EarnS`) by firm-size | QWI | #223 `e6_e7` | **aggregate-relative** EarnS floor | **gated** |
| E8 | nonemployment incidence/duration by age | SIPP holdout | #212 `e8_nonemployment_by_age` | \|log share ratio\| (any/long) | **gated** |
| E9 | earnings-change dist. by transition type | SIPP holdout | #212 `e9_transitions` | j2j: median + IQR gaps; stay: none (both floors degenerate) | **j2j gated; whole stay cell report-only** (B5) |
| E10 | regression gate: locked PSID gates still pass | existing `gates.yaml` | existing gate-1/2 floors | unchanged | **gated** (always) |
| E11 | aggregate J2J flows by origin × destination size | LEHD J2JOD (#228) | #228 extract; margin floor PENDING #223 | margins: PENDING; detail: none derivable | **aggregate margins proposed gated; 5-quarter detail report-only** (§7); certifies no person link |
| E12 | aggregate assignment audit plus linkage/sorting aspiration | public grouped margins / future linked source | aggregate floor PENDING; linkage floor unavailable | strict claims split (§8) | **strong E12 deferred**; future aggregate audit may certify observable margins only |

Per-gate detail follows.

### E1 — employment share by firm-size × sector (SUSB)

- **Cells**: five canonical IC2 bands (`LT10`…`B500_PLUS`) × NAICS
  sector, from `data/external/susb_us_sector_size_2022.csv`;
  calibration consumes the same source's *margins*, so the E1 gate
  axis must be the residual structure (see §10).
- **Floor problem** (#223 `method_findings.e1_no_sector_replicate`):
  the committed SUSB extract is a single 2022 cross-section — no
  same-source temporal/resampling floor exists for size × sector.
  The committed composite is (a) SUSB published noise-flag CV bounds
  per cell (G ⇒ CV ≤ 2%, H ⇒ ≤ 5%, J ⇒ unbounded) and (b) a BDS
  year-over-year national size-margin stability floor, stated on the
  coarsened partition keeping `20_99` whole
  (`method_findings.e1_bds_straddle`; `bds_fsize_to_canonical` is
  inexact across the 50 edge).
- **Recommendation (revised under B1): E1 does not gate at first
  lock.** The previous draft gated the national size margin on the
  BDS-stability + CV composite, on the reasoning that the coarsened
  BDS partition "is not something calibration targets". It is —
  exactly, not approximately: per #223's committed groups `1_9` =
  LT10 and `10_19` + `20_99` = B10_49 + B50_99 once `20_99` is kept
  whole, so the coarsened margin is a **merge** of the SUSB margins
  calibration consumes. Scoring it measures source agreement and
  calibration convergence, neither of which a candidate can move.
  House precedent is directly on point: `gates.yaml`
  `not_certified.stock_margins` — "the trivially-passable-stock
  problem". Both the margin and the size × sector cross publish
  report-only, with the CV/BDS composite floor retained as the
  published diagnostic; noise-flag-J cells stay excluded.
- **What would make E1 gate**, registered for the referee (§10.6):
  either calibration stops consuming SUSB size × sector margins (a
  joint-PR change to frozen ADR 0003, trading calibration fit for
  gate power), or a genuinely held-out firm-side axis is committed
  with a floor. The old "CV bounds alone as the floor term"
  alternative does not help — it changes the floor, not the fact
  that the statistic is a function of the targets.
- **Substantive tolerance**: 5% relative share error PROPOSED
  (ECPS-convention "±5% of administrative statistics").

### E2 — hire/separation/J2J rates by sex × age (LEHD J2J)

- **Reference**: the #228 `j2j_us_sexage_2015on.csv` extract
  (national, 2015Q1–2025Q1; note LEHD `se` is sex×education — sex×age
  is the `sa` tabulation, verified empirically and test-pinned).
  This is a held-out **gate axis** per ADR 0003: calibration touches
  firm-size × sector flow margins only, never the demographic axes.
- **Floor**: the committed #223 `e2` block floors the aggregate-side
  firm-size cells (36 same-quarter YoY pairs; full and ex-pandemic
  variants both committed per
  `method_findings.cycle_signal_in_floors`). The sex × age floor
  itself is a required pre-lock build on the #228 extract, same
  method (#223 `method_findings.e2_no_age_sex_axis` recorded the
  deferral explicitly).
- **Recommendation**: **ex-pandemic** YoY \|log ratio\| floors
  (e.g. firmsize1 hire rate: full 0.0565 ± 0.0549 vs ex-pandemic
  0.0273 ± 0.0211). Rationale: the full-sample floor treats the
  2020–2021 shock as noise and would roughly double every tolerance;
  a model should not get credit for pandemic-sized errors in normal
  years. The **full-sample** variant stays on the record as the
  referee alternative (argument for it: candidates will be scored on
  periods that include shocks).
- **Unit caveat** (ADR 0003): J2J counts jobs, not persons, and the
  #228 extract is ownership `oslp`; §11 carries the disposition.
- **Substantive tolerance**: 10% relative rate error PROPOSED.

### E3 — tenure distribution by age (CPS tenure supplement)

- **Cells**: BLS age bands × supplement years 2020/2022/2024
  (`PTST1TN`, `PWTENWGT`; reader per #205).
- **Degeneracy finding** (#212 `tenure_floors_draft_v0.json`,
  `heaping_caveat`): reported tenure heaps on integers, so
  half-vs-half quantile-gap floors are exactly zero in 36/63 cells —
  a degenerate threshold basis.
- **Recommendation**: state E3 on the **weighted-ECDF max-gap**
  (heaping-robust; non-degenerate in every cell, e.g. 2020 25–34:
  0.018 ± 0.0059). The quantile-gap formulation stays committed as
  the referee alternative, but adopting it would require an
  arbitrary substantive tolerance to paper over the zeros.
- **Floor rule across years** (registered in the block YAML as
  `year_rule` / `derivations.floor_selection: per_cell_own_year`):
  the cells are the full 3 × 7 = **21** (year, band) pairs, and each
  cell's threshold derives from **its own year's** floor
  (`by_year.<year>.<age_band>.floor_ecdf_max_gap`). Floors are not
  pooled, averaged, or worst-of'd across years — #212 floors each
  supplement year separately, so per-year is the only rule its
  evidence base supports. Stated here because a bare cell-count pin
  with a free `<year>` placeholder would harden the ambiguity rather
  than resolve it.
- **Substantive tolerance**: ECDF max-gap 0.02 PROPOSED (comparable
  to the largest observed adult-band floor means).

### E4 — employer-retention pairs by age × sex (SIPP holdout)

- **Cells**: 6 age bands × sex, monthly same-employer retention
  (#212 `e4_retention_by_age_sex`; person-disjoint sha256
  half-splits, seeds 0–4, WPFINWGT-weighted; all 12 cells non-thin,
  floors 0.0003–0.0020 \|log ratio\|).
- **Recommendation**: gate on \|log rate ratio\| with the uniform
  policy. Because retention rates sit near 1, the floor is tiny;
  the substantive tolerance term (PROPOSED: \|log ratio\| 0.005,
  ≈ 0.5% of the retention rate) is the operative bound in most cells
  — deliberately: retention is exactly the moment a chained model
  understates.
- **Prerequisites**: the §6 seam ruling (half-splits share SIPP's
  seam structure — `seam_caveat` in the artifact) and the §9
  first-lock linkage audit (E4 is in the minimal-viable-audit scope).

### E5 — multi-window attachment runs by age (SIPP holdout)

- **Cells**: 6 age bands, full-year same-employer run share
  (#212 `e5_runs_by_age`; floors 0.011–0.049 \|log ratio\|, all
  non-thin). This is the employer analogue of the gate-1 runs view:
  window-2 moments cannot see chained-persistence understatement, so
  E5 is the load-bearing persistence gate and must be **gated**, not
  report-only.
- **Recommendation**: uniform policy on \|log share ratio\|;
  substantive tolerance \|log ratio\| 0.05 PROPOSED. Same §6/§9
  prerequisites as E4 (E5 is the second member of the
  minimal-viable-audit scope).

### E6 — worker-flow rates by firm-size × sector (QWI)

- **Cells**: QWI firm-size groups (mapped through
  `firms/banding.py`; `firmsize1` "0–19" is an inexact
  `LT10+B10_49` span, recorded) × sector, hire and separation rates
  (#223 `e6_e7`; 36 YoY pairs, full and ex-pandemic committed).
- **Recommendation (revised under B1): E6 does not gate at first
  lock.** The previous draft had the reasoning inverted: it demoted
  the sector × size cells for being "close to the calibration
  margin" when those cells **are** the calibration targets, and
  gated their job-weighted aggregate — the size margin — where the
  per-cell miss terms average out. Under calibration convergence
  that aggregate passes by construction; under non-convergence it
  reports calibration residual. Both publish report-only with
  ex-pandemic floors retained as diagnostics.
- **Substantive tolerance**: 10% relative rate error PROPOSED.

### E7 — mean earnings by firm-size (QWI `EarnS`)

- **Unit rule** (ADR 0003, restated §11): QWI publishes **mean**
  monthly earnings of full-quarter employees, never medians; E7 is
  stated on means.
- **Finding** (#223 `method_findings.e7_nominal_trend`): raw EarnS
  YoY variation embeds aggregate nominal wage growth — a trend, not
  noise. Both the raw and the **aggregate-relative** (cell relative
  to the all-size aggregate) floors are committed.
- **Unratified proposal — REFEREE/PENDING**: gate on the
  **aggregate-relative** EarnS
  moment (the size *gradient* of earnings, which is what firm-size
  policy needs) with its ex-pandemic floor; the raw-level cell is
  report-only. Referee alternative: gate raw levels with a
  deflation rule (requires choosing a deflator — a new registered
  input).
- **Substantive tolerance**: 5% relative gradient error PROPOSED.

### E8 — nonemployment incidence and duration by age (SIPP holdout)

- **Cells**: 6 age bands × {any-nonemployment share, long
  (multi-month) nonemployment share}
  (#212 `sipp_e8_e9_floors_draft_v0.json`; floors 0.05–0.20
  \|log ratio\|, all non-thin; censoring-free 12-month-observed
  restriction recorded in the artifact and carried into the cell
  definition).
- **Recommendation**: uniform policy on \|log share ratio\|;
  substantive tolerance \|log ratio\| 0.10 PROPOSED. E8 needs no
  worker-to-firm link (ADR 0004 §4), so it has no linkage
  prerequisite.

### E9 — earnings-change distribution by transition type (SIPP holdout)

- **Cells**: transition classes {stay, j2j} × {median log change,
  IQR log change} (#212 `e9_transitions`; entry/exit earnings-change
  cells are not defined — one side has no earnings).
- **Degeneracy finding** (`stay_median_heaping_caveat`): within-job
  SIPP monthly earnings are wave-constant under dependent
  interviewing, so the stay median log-change heaps at exactly 0 and
  its floor is degenerate (0.0/0.0) — same failure class as the E3
  integer heaping.
- **Recommendation (revised under B5): the stay cell does not gate
  at first lock — both its statistics are report-only.** The
  previous draft gated stay on the IQR, presenting it as the
  non-degenerate escape from the median's 0.0/0.0 floor. It is not:
  `sipp_e8_e9_floors_draft_v0.json`
  `e9_transitions.earnings_change.stay.floor_abs_iqr_gap` is
  **also** `{mean: 0.0, sd: 0.0}`, so the "IQR-only" gate was 100%
  the hand-set 0.02 with no stated basis — a hand-set number
  gating alone, which the campaign rule forbids. Both stay
  statistics publish as report-only identity checks (a model
  reporting a nonzero stay median or a non-degenerate stay IQR is
  informative, and worth seeing, but neither can gate against a
  degenerate floor). The referee's alternative — defend 0.02 —
  was available and is declined: the honest defence would have to
  be a substantive claim about how much within-job earnings
  variation a model may invent, and SIPP cannot measure that
  quantity at all under dependent interviewing, so any number
  would be invented rather than derived. Gate **j2j on both** median
  (0.2264, floor 0.0766 ± 0.0345) and IQR (1.069, floor
  0.0842 ± 0.0522). Referee alternative for stay: a full
  distributional distance (e.g. the harness energy-distance block)
  — richer, but no floor is committed for it, so it cannot gate at
  first lock (floors-before-thresholds).
- Note the j2j cell counts 545 unweighted pairs — above the thin
  flag but the thinnest gated cell in the block; recorded.
- **Prerequisite**: §9 (E9 consumes transition classification).
  Its firm-size-conditional variants are **not** in the first lock
  are **permanently report-only** under §9.1 Tier 0 (no admissible
  truth frame — permanent, not awaiting ratification).

### E10 — regression gate (locked PSID gates)

- **Definition**: after the spell layer attaches, every already
  locked PSID earnings gate (`gates.gate_1` and successors) must
  still pass, under its existing thresholds and floors, unchanged.
- **No new floor, no new threshold, nothing PROPOSED**: E10
  re-scores existing locked cells.
- **Hard rule** (ADR 0004 §4, adopted): **linkage failure never
  weakens E10**. An invalid or failed employer-side cell cannot be
  traded against, or used to reinterpret, any PSID threshold; E10 is
  gated from the first lock and in every subsequent phase.

### E11 — J2J flows by origin × destination firm size — see §7.

### E12 — within/between-firm variance and coworker correlation — see §8.

## 4. Degenerate-floor register

For the referee's convenience, the committed degeneracies the block
must not gate on directly:

1. **E3 tenure quantile gaps**: exactly 0.0 in 36/63 cells (integer
   heaping) → ECDF max-gap is an unratified proposal (#212).
2. **E9 stay median AND stay IQR**: *both* floors exactly 0.0/0.0
   (wave-constant reporting under dependent interviewing) → the
   whole stay cell is report-only (#212; corrected under B5 — the
   previous version of this register listed only the median and
   presented the IQR as the non-degenerate escape, which it is
   not).
3. **E1 sector axis**: no floor derivable from committed extracts
   (single-vintage SUSB) → report-only (#223).
4. **E11 detail cells**: no floor derivable (five-quarter published
   window, no YoY pair structure) → report-only (#228, §7).
5. **E12**: no reference extract at all → deferred (#223, §8).

Distinct from all five, and not a floor degeneracy: **E9/E11
firm-size-conditional cells** have no admissible *truth frame*
(§9.1). The five above are cells whose floor cannot be measured;
those are cells whose target quantity has no per-record referent at
all. They are **permanently** report-only — the status must carry
that permanence explicitly, since "report-only" elsewhere in this
block means "unratified pending evidence", which these can never
become.

## 5. Views and cell registration (schema sketch)

Following the `views:` convention of `gates.yaml`, the amendment PR
registers (names PROPOSED):

- `sipp_job_spells` — loader `populace_dynamics.data.sipp_jobs`,
  pu2023 (ref. year 2022), person-disjoint holdout, WPFINWGT;
  feeds E4/E5/E8/E9; floor-run paths, deployment-scale conversion,
  and digests are **PENDING #212** and cannot be copied into the block
  YAML before that promotion is approved and merged.
- `cps_tenure` — CPS Jan supplements 2020/2022/2024; feeds E3;
  floor-run path and digest: **PENDING #212**.
- `employer_firm_targets` — the committed
  `data/external/{susb,bds,qwi,j2j,j2jod,j2j_sexage}_us_*.csv`
  extracts (external references, never scored model output);
  feeds E1/E2/E6/E7/E11; final floor-run path and digest:
  **PENDING #223**.

## 6. The seam ruling (formal proposal, from #214)

`runs/seam_reconciliation_draft_v0.json` measured, on linked SIPP
job-months: within-wave monthly separation ≈ 1.7–1.8% (means 0.0171
file-year 2022, 0.0182 file-year 2023) against a Dec→Jan across-wave
seam rate of **9.45%**, while the J2J national benchmark's
monthly-equivalent main-job separation rate runs ≈ 3.5–4.6%. The
artifact's concept deltas (jobs-vs-persons, main-job-vs-all-jobs,
UI-covered universe, the 1−(1−q)^{1/3} approximation) are carried
into the record, including the naming note that SIPP's ~0.35%
person-level direct J2J rate and Census J2J's separation benchmark
are different universes, not a contradiction.

**Proposed ruling (to be ratified by this referee round — the
artifact itself is marked NOT RATIFIED):**

1. **J2J is truth for rate LEVELS** (separation/hire/J2J levels in
   E2/E6 gate against the LEHD references, not against SIPP's
   seam-distorted levels).
2. **SIPP is truth for persistence STRUCTURE** (E4/E5/E8/E9
   conditional and distributional shape — J2J publishes no
   within-person structure).
3. **Phase-1 hazards are estimated seam-aware**: wave-frequency
   estimation with within-wave interpolation, so the 5.5× within-wave
   vs seam contrast never enters a hazard as if it were a real
   monthly time-pattern.

**Cross-wave check delivered, operative interpretation PENDING.**
#235 is a disclosed re-analysis, not a pre-registration. From its
committed counts, excess re-key signature is 15.12% on E→E
separations (`PASS_WITH_CORRECTION_BAND` under the unratified bands)
and 9.36% after scaling to all separations (`PASS`). The one-sided
95% uppers are 17.65% and 10.92%, respectively. Its author-proposed
15%/30% bands and operative population remain `REFEREE`; this
control document chooses neither. This is the first item in Vahid's
2026-07-30 continuation comment and must be settled before promotion.

Whichever population is chosen, the scale direction is explicit:
E→E-conditional excess may be multiplied by the observed E→E share
of all seam separations to produce the all-separations excess.
The inverse operation is not an evidentiary correction, and neither
quantity is a correction to the measured 9.45% seam separation rate.
The seam ruling above therefore remains proposed, with its confidence
framing PENDING the population and band decisions.

## 7. E11 — the window decision (explicit referee choice)

Material finding from #228, test-pinned (`test_j2jod_detail_window`):
the national origin × destination firm-size cross in J2JOD is
published **only 2015Q1–2016Q1** — five quarters. From 2016Q2 every
detail cell carries status flag 11 (a state coverage gap propagated
to the national aggregate; J2J Explorer suppresses identically).
The one-sided margins run through 2025Q1.

Vahid's 2026-07-30 synthetic-layer decision records the strict
claims boundary: grouped size/industry employment, mean-earnings,
and flow reproduction can support an **aggregate assignment audit**;
it cannot establish true linkage, coworker sorting, within/between
variance, firm effects, or spillovers. E11 is therefore an
aggregate-only statistic under either option below. A pass never
means that a SIPP/CPS worker has the correct firm or coworkers.

The referee round must still choose between:

- **(a) Aggregate margins-gated + detail report-only.** Gate the
  origin-size and destination-size margins (the `ee_hire_rate` /
  `ee_separation_rate` cells whose final floor is PENDING #223),
  on the referee-selected temporal basis; score the full 6×6 detail
  on the 2015Q1–2016Q1
  window **report-only**. Rationale: a five-quarter window supports
  no temporal-stability floor (floors-before-thresholds forbids
  gating it), and a gate pinned to a nine-year-old suppressed
  vintage would be an evidentially weak lock; but the detail window
  is still the only published look at the size ladder, so it stays
  on the record.
- **(b) Detail-gated on the five-quarter window.** Requires the
  referee to accept a non-temporal floor basis (e.g. noise-infusion
  margin slack) and the vintage staleness; on the record as the
  alternative.

Under (a), ADR 0004's E11 ordered-pair linkage rules attach to the
report-only detail cells and to the margins-gate's origin/destination
assignments respectively; the joint-pair audit becomes operative only
if (b) is chosen or the detail cell is later promoted.

For first lock, no person-level E11 origin/destination assignment is
certified. The gate-eligible object in (a) is the grouped flow margin
itself, held out under §10; linkage QC cannot be inferred from its
aggregate fit.

## 8. E12 — two-tier claims boundary; strong form deferred

Vahid's decision record on issue #282 adopts the “both” posture with
a strict scope:

1. **Aggregate assignment audit**: a future, separately floored audit
   may certify reproduction of observable grouped size/industry
   employment, mean-earnings, and flow margins. It certifies those
   margins only. Its exact statistic, calibration/gate partition, and
   noise floor remain `PENDING`; no aggregate E12 threshold is
   introduced by this revision.
2. **Linkage/sorting E12**: true coworker assignment,
   within/between-firm variance, worker sorting, firm effects, and
   spillovers require linked employer-employee evidence and an audit at
   the co-assignment unit. No current public source can power that
   test. This strong form remains a registered aspiration and a
   no-go boundary for those claims.

Thus strong E12 is **deferred** in the first IC3 block: definition
recorded, no threshold, no floor, and no `locked: true` claim.
Passing E11 or any later aggregate audit may support grouped-margin
representativeness; it may not be cited as observed linkage,
firm-identity, coworker, variance-decomposition, causal firm-effect,
or spillover validation. The synthetic firm register remains usable
for explicitly firm-size-keyed policy analysis under that limitation.

## 9. Linkage-QC integration (ADR 0004 as amended)

ADR 0004 is adopted **with the three changes from the Workstream B
review** (PR #224 review comment), which this block operationalizes:

1. **Minimal viable audit scope for the first lock.** The full
   two-arm, five-band × NAICS-major × transition-class × primary_job
   powered audit would move the lock well past the #192 schedule.
   First lock therefore audits **E4/E5 SIPP-internal employer
   attachment only** — the assignment where hand-adjudicable truth
   demonstrably exists (within-panel `EJB` job-ID attachment, with
   the §6 cross-wave ID check as its natural companion artifact).
   The full grid (E9 transition classes, E11 ordered pairs) phases
   in behind it; a gate promoted later (e.g. E11 detail) must clear
   its ADR 0004 audit at promotion time, never inherit the E4/E5
   pass.
2. **Phase-1 imputed-band adjudicability — answered in §9.1, not
   left to the round.** The draft previously carried this as a
   blocking open item (§13 item 6). It is now answered, because the
   answer determines what the referee is being asked to ratify: no
   admissible per-record truth frame exists, and per-record
   adjudication is not a well-posed question for a draw-based
   imputation at all. The degradation ladder for E9/E11
   firm-size-conditional cells is registered in §9.1. First lock
   still scopes those conditional cells out (§3-E9, §7) — but now
   for a stated reason rather than by avoidance.
3. **Named owners.** Workstream B (@vahid-ahmadi) owns the
   **firm-side sidecar specification** (schema, versioning; sidecars
   join IC1 on `person_id`/`spell_id`, never amend IC1) and the
   firm-side audit artifacts. Workstream A (@daphnehanse11) owns the
   E4/E5 SIPP-internal adjudication frame and coder-panel operation.
   Numeric `P_floor`, `P_design`, α, power, and the recall-gating
   decision are referee items (ADR 0004 §6.1), not owner decisions.

Unchanged ADR 0004 rules restated as binding on this block: audit
precedes the one-shot run; passing uses the one-sided confidence
bound, not the observed proportion; a failed floor invalidates the
cell (no threshold shopping); linkage failure never weakens E10.

### 9.0 Linkage-bias reweighting (ADR 0004 §3)

**Closes blocking item B4.** #224 is three-part by its own title —
precision floors, adjudication samples, **linkage-bias
reweighting** — and the previous draft operationalized the first
two and silently dropped the third, while §13 claimed to enumerate
"every decision this draft leaves to the referee". First-lock
scoping to E4/E5 narrows the strata; it does not repeal §3. E4 and
E5 are link-consuming gated cells, so ADR 0004 §3.4 binds them:
every link-consuming cell publishes **weighted and unweighted**,
with the operative version chosen **before candidate results are
seen**.

Instantiated at first-lock scope, from Workstream A's offer
(2026-07-22) with the B-side registrations added:

- **Analysis unit**: E4 uses the adjacent-month job-pair; E5 uses the
  maximal same-ID run registered by #236. A pair-level score cannot
  automatically weight a run. **Clustering**: worker for both units
  (a person contributes many pairs/runs; they are not independent).
- **Target reference populations**: E4 targets all eligible
  adjacent-month job-pairs in the #235 population—384,747
  within-wave job holdings plus 10,828 seam holdings, retained as
  separate risk strata. E5 targets the corresponding maximal-run
  frame defined in #236. Neither target is the adjudicated subsample;
  reweighting carries audit results from each sampled arm to its
  registered frame and never pools across the seam axis.
- **Candidate observables `X`**: age band, sex, industry section,
  establishment-size code (IC2 span, inexactness carried), earnings
  tercile, multi-job flag, and the **seam-vs-within indicator**;
  E5 additionally includes pre-link run-length stratum —
  the last is load-bearing, since #214/#235 establish the seam as
  the dimension along which attachment behaviour differs most.
- **Weight construction**: separate pair- and run-unit inclusion
  propensities over their registered `X`, with the functional form
  and any trimming left REFEREE. Audit sample-inclusion weights and
  later linkage-bias weights remain distinct.
- **Overlap/balance tolerances, trimming percentile, propensity
  specification**: REFEREE (ADR 0004 §6.4) — added to §13 as item
  17.
- **Operative version** (weighted vs unweighted) for E4, E5 and —
  when they promote — E9, E11, E12: REFEREE, registered **before**
  any candidate scores exist, per §3.4. Added to §13 as item 18.
- **Publication rule**: both versions publish for every
  link-consuming cell regardless of which is operative; a divergence
  between them is itself a reportable finding, not a nuisance to be
  resolved silently.

Not in first-lock scope but registered so promotion cannot skip it:
E9, E11 and E12 acquire their own §3 instantiation at promotion
time, never inheriting this one (the §9 no-inheritance rule).

### 9.1 Imputed firm-size bands: no admissible truth frame

**The finding.** There is no admissible per-record truth frame for a
QRF-imputed firm-size band on a CPS host, and the deeper problem is
that ADR 0004's machinery presupposes something the imputation does
not produce.

**Why no candidate source qualifies.** Four exist and each fails on
its own terms:

| candidate | why it cannot serve as truth |
|---|---|
| CPS ASEC `NOEMP` | it **is** the training label. Scoring an imputation against its own label measures fit, not accuracy — and `NOEMP` describes the *preceding calendar year's longest job*, not the spell being scored (ADR 0003 reference-period mismatch), so it is not even a description of the right object |
| SIPP `EJB{n}_EMPSIZE` | measures **establishment** size, not enterprise size (#192 finding 1) — a different quantity, not a noisier reading of the same one. Also a different sample: SIPP persons are not the CPS hosts being scored |
| LEHD / SUSB administrative firm size | the true quantity, but there is no public linkage from an administrative employer record to a public-use CPS person. This is the same wall E12 hits (§8) |
| pre-redesign SIPP (2008 panel) | worker-reported all-locations firm size, representative and jointly observed with tenure — the ADR 0003 conditioning bridge. Still a *self-report* (a noisy measure), aged to 2008-2013, and again a different sample from the CPS hosts |

**Why the question is ill-posed, not merely unanswerable.** ADR 0004
is written for an *assignment*: a matcher claims that this record and
that record are the same employer, and a coder can in principle
adjudicate whether they are. Precision and recall are defined
because each unit has a true class.

A QRF imputation makes no such claim. It draws a band from a
conditional distribution given the host's covariates. The draw is not
an assertion that this person worked at a firm of that size; it is a
realization chosen so that the *population* carries the right joint
distribution. There is no fact of the matter about an individual
draw to be right or wrong about, so "precision of the imputed band"
has no referent — even with perfect administrative data in hand, a
correctly specified imputation would score arbitrarily badly per
record, and a degenerate one that always emitted the modal band
would score better.

Reporting a per-record precision for imputed bands would therefore
be worse than reporting nothing: it would be a number that improves
as the model gets worse.

**The consequence that actually binds.** A gate on a
firm-size-conditional cell, where the conditioning band is imputed
and the reference margin is one the model was calibrated to, tests
the **calibration**, not the model. It passes by construction. This
is the trap the ladder below exists to prevent, and it is a
different failure from the E12 identification gap: E12 lacks a
reference; this lacks an *independent* one.

**Registered degradation ladder.** What person-level E9/E11 outcomes
conditioning on an imputed band degrade to, in force from first lock:

- **Tier 0 — permanent report-only, per the round-1 disposition.**
  The rule below is carried **verbatim** from Workstream A's §13
  item 6 response, per the referee's round-1 disposition
  ("Workstream A's permanent-report-only-with-degradation-rule is
  the right shape; carry the rule verbatim into the draft YAML, not
  the comment thread"):

  > "Cells conditioning on imputed firm-size bands are validated
  > distributionally (calibration fit to SUSB margins plus
  > held-out-axis stability) and are report-only in every phase;
  > they gate only if an external person-level truth source
  > materializes, at which point they enter through the standard
  > promotion ceremony (new floor + ADR 0004 audit)."

  The later 2026-07-30 #282 decision clarifies the scope: this
  permanent disposition binds person-level cells whose interpretation
  requires the imputed band to be correct for that person. It does not
  prevent a genuinely held-out **aggregate** grouped-margin audit from
  certifying reproduction of that margin under §7/§8. Such an
  aggregate pass still certifies no individual assignment.

  The word doing the work is **permanent**: report-only here does
  not mean "awaiting ratification", it means the cell has no
  admissible referent and no amount of further evidence of the
  present kind changes that. The status label must say so, or a
  later reader will mistake it for the ordinary unratified case.

  *(Drafting note, for the referee: an earlier revision of this
  section proposed excluding these cells under a distinct
  `no_admissible_truth_frame` status rather than publishing them
  report-only, on the reasoning that report-only implies a
  measurement whose status is merely unratified. That is a labelling
  disagreement, not a substantive one, and the round-1 disposition
  settles it toward report-only. It is recorded here rather than
  dropped because the concern it encodes — that "report-only" reads
  as provisional — is exactly what the permanence wording above
  must defeat.)*
- **Tier 1 — calibration identity, never called validation.** The
  imputed band marginal must reproduce its SUSB/QWI calibration
  target. This is a build check: it is near-tautological, it is
  registered as such, and it may not be cited as evidence the band
  imputation is correct.
- **Tier 2 — aggregate audit on a genuinely disjoint margin.** A
  grouped firm-size statistic becomes gate-eligible only against a
  reference margin **not used in calibration**, per the ADR 0003
  disjoint partition already registered in §10. E11's origin ×
  destination ladder is the live example: the size *margins* are
  calibration targets, so the ladder's off-diagonal structure is the
  only part carrying independent information. Promotion also
  requires a committed floor first (floors-before-thresholds), which
  §7 shows the five-quarter detail window does not currently
  support. Tier 2 certification stops at aggregate reproduction and
  never promotes the underlying person-level band assignment.
- **Tier 3 — full per-record adjudication: only with a linked
  reference.** Gated on the same condition as E12 (§8). If a linked
  employer-employee reference ever becomes available, ADR 0004's
  audit machinery becomes applicable *and required* at promotion
  time; a cell promoted then never inherits the E4/E5 pass (§9 item
  1).

**Scope note.** This section is about *imputed* bands only. E4/E5
SIPP-internal employer attachment is unaffected: that is a genuine
assignment with hand-adjudicable truth, which is exactly why §9 item
1 scopes the first-lock audit to it.

**What the referee is asked to ratify** (replacing the old §13 item
6): the ill-posedness finding, the four-source refutation, and the
four-tier ladder. The ladder's Tier 0 carries Workstream A's rule
verbatim per the round-1 disposition; what is newly asked of the
round is (a) the ill-posedness argument as the *stated basis* for
that rule — round 1 accepted the shape without one on the record —
and (b) Tier 2's rule that a calibrated margin can never serve as
the reference for a cell conditioned on it, which is the same
partition-integrity principle as blocking item B1 applied to
conditioning variables rather than to gated statistics.

## 10. Calibration/gate cell partition (exhaustive, E1-E12)

**Re-issued in full to close blocking item B1(ii).** The previous
version listed two calibration families and four gate axes and
omitted E6 and E7 on both sides — an enumeration that cannot
support a mutation test, because a gate with no registered cells
has nothing to mutate. This version enumerates every gate, its
disposition, and the reason it is or is not disjoint from fitting.

### 10.1 The ONLY quantifier (binds every fitting stage)

Registered as binding, not as description:

> **No stage that fits, calibrates, reweights, or tunes any part of
> the employer layer may consume any statistic listed in §10.3, on
> any source, at any aggregation, in any phase.** "Stage" means
> `microcalibrate` reweighting, phase-1 transition-hazard
> calibration, QRF hyperparameter selection, and any post-hoc
> alignment or raking step, whether or not it is called
> calibration.

The old §10 constrained `microcalibrate` alone. #192 phase 1 has
hazards "calibrated to QWI/J2J", so hazard calibration was an
unregistered consumer — which left the E2 sex × age and E11-margin
holdouts unenforceable exactly where they matter. The quantifier
above closes that; the draft YAML (B2) carries the §10.3 list in
machine-checkable form so a dropped, added, or renamed cell fails a
test.

**Corollary, registered explicitly** (§9.1): a statistic is not
held out merely because calibration did not target it *by name*. A
deterministic function of calibration targets — a margin, a merge,
a coarsening, any linear functional — is a calibration target. This
is the test B1 applied to E1 and E6, and it is the test §10.3 must
be read under.

### 10.2 Calibration inputs (consumed by fitting; never gated)

- **SUSB employment margins**: canonical size band × NAICS sector
  (`susb_us_sector_size_2022.csv`), SUSB universe (private, ex
  NAICS 92, crop/animal production, non-employers; `class_of_worker`
  scoping per IC1).
- **QWI flow margins**: firm-size × sector hire and separation rates
  (`qwi_us_firmsize_sector_2015on.csv`, ownership `op`).
- **Every deterministic function of the above**, per §10.1's
  corollary — including the national size margins of both, and the
  BDS coarsened partition (`1_9` = LT10 exact; `10_19` + `20_99` =
  B10_49 + B50_99 exact once `20_99` is kept whole), which is a
  merge of the SUSB margins calibration consumes.
- **Phase-1 hazard-calibration references**: the J2J/QWI *national
  flow levels* used to set hazard rates per the #214 seam ruling
  (J2J for levels). Registered here as a fitting input so §10.1
  binds it.

### 10.3 Gated cells (held out from every fitting stage)

| gate | gated cell family | disjointness basis |
|---|---|---|
| E2 | sex × age hire/sep/J2J rates (#228 `sa` extract) | demographic axes; no fitting stage consumes a sex- or age-crossed statistic |
| E3 | tenure ECDF max-gap by age (CPS supplement) | different source; not a calibration input |
| E4 | employer-retention pairs by age × sex (SIPP holdout) | different source, held-out persons |
| E5 | multi-window attachment runs by age (SIPP holdout) | different source, held-out persons |
| E7 | **aggregate-relative** `EarnS` gradient by firm size | calibration consumes QWI *flow* margins (hire/sep), never `EarnS`; earnings is an untouched axis of the same file |
| E8 | nonemployment incidence/duration by age (SIPP holdout) | different source, held-out persons |
| E9 | j2j earnings-change median + IQR (SIPP holdout) | different source, held-out persons |
| E10 | the locked PSID gates, re-scored | PSID; disjoint by construction |
| E11 | aggregate destination-size EE flow **margins** (J2JOD) | J2JOD is not a calibration input; certifies aggregate reproduction only (§7) |

**E11 caveat, registered rather than assumed.** J2JOD margins are
not consumed by fitting *as committed*, but they are close kin to
the QWI/J2J flow margins that are. They stay gate-eligible on the
condition that §10.2's hazard-calibration references are pinned to
the QWI/J2J extracts and never extended to J2JOD. If a future
phase calibrates to J2JOD, E11 margins move to §10.4 by this
rule, without a further referee round.

### 10.4 Report-only at first lock (not gated)

| gate | cell family | why not gated |
|---|---|---|
| **E1** | national size margin **and** size × sector cross | **B1**: both are deterministic functions of the SUSB margins calibration consumes. The coarsened BDS partition is an exact merge of them, so scoring it tests source agreement and calibration convergence — neither of which a candidate can influence. House precedent: `gates.yaml` `not_certified.stock_margins`, "the trivially-passable-stock problem". The CV/BDS composite floor is retained as a published diagnostic |
| **E6** | size margin **and** size × sector cells | **B1**: the size margin is a job-weighted aggregate of the calibrated size × sector cells — a linear functional of calibration targets. Under convergence it passes by construction; under non-convergence it measures calibration residual. The old draft had this inverted, demoting the sector cells (the literal targets) while gating their aggregate, where miss terms average out. Floors retained as diagnostics |
| E7 | raw `EarnS` levels | nominal trend, not noise (#223); the gradient carries the signal |
| E9 | stay median **and** stay IQR | both floors degenerate — see §4 and §11.4 (B5) |
| E11 | 5-quarter origin × destination detail | no temporal replicate: one YoY pair per cell (#223 v1 `e11.detail_window`) |
| E9/E11 | any person-level outcome conditioned on that person's imputed firm-size band | §9.1 Tier 0 — no admissible per-record truth frame, **permanently** report-only |
| — | firm-age axis (QWI/BDS) | held-out axis registered, but no committed extract or floor |
| — | state axis (QWI state-level) | held-out axis registered, no committed extract or floor |

### 10.5 Deferred (cannot lock)

| gate | status |
|---|---|
| E12 strong linkage/sorting form | no adjudicable linked reference exists (§8); strict claims no-go attaches |
| E12 aggregate form | statistic, disjoint partition, floor, and threshold all PENDING a later promotion (§8) |

### 10.6 What B1 costs, stated plainly

Demoting E1 and E6 leaves the first lock gating **E2, E3, E4, E5,
E7, E8, E9(j2j), E10, E11(margins)** — nine gates, of which only
E2, E7 and E11-margins are firm-side. The employer block's
firm-side gating power at first lock is therefore thinner than the
#192 plan implied, and this document should not disguise that: the
alternative on offer is not a stronger block but a block whose
firm-side gates pass by construction.

Two routes exist to restore firm-side power, both out of scope for
first lock and both registered here as the honest options: (a) stop
calibrating to QWI flow margins and gate them instead — a joint-PR
change to the frozen IC2/ADR 0003 partition, trading calibration
fit for gate power; (b) commit a genuinely held-out firm-side
reference (firm-age or state axis) with a floor, promoting through
the standard ceremony.

## 10A. Substantive-tolerance basis register (B5)

Under `threshold = max(floor mean + 4·sd, substantive_tolerance)`
the hand-set term **is the operative threshold** wherever the floor
is small or degenerate. Round 1 found seven tolerances with no
stated basis. The campaign rule is that a hand-set number may gate
only as an explicitly disclosed policy choice **with a rationale**,
so each is given one here or the cell stops gating.

| tolerance | value | operative? | basis |
|---|---|---|---|
| E1 | 5% relative share | n/a — report-only under B1 | ECPS convention ("±5% of administrative statistics"). Retained for the published diagnostic |
| E2 | 10% relative rate | rarely (floors 0.055–0.097 dominate) | a 10% error in a demographic-specific hire/separation rate changes the implied annual turnover of that group by ~1pp at observed levels — below the smallest published J2J demographic gradient the model is meant to reproduce. Disclosed policy choice |
| E3 | 0.02 ECDF gap | often | largest adult-band ECDF floors (#212); a 2pp shift in the tenure CDF at any point is ~0.4 years at observed density — within the CPS supplement's own rounding |
| E4 | 0.005 \|log ratio\| | most cells (floors 0.0003–0.0020) | anti-**understatement** posture, stated: the E4 floors are so tight that floor+4·sd would gate on differences no consumer could act on. 0.005 is ~0.5% relative retention error. Deliberately the binding term |
| E5 | 0.05 \|log share ratio\| | sometimes (floors 0.011–0.049) | one order of magnitude above the E4 bound, reflecting that multi-window run shares compound single-window error over the window length (ADR 0004 §4's compounding argument, applied to tolerance rather than to audit) |
| E6 | 10% relative rate | n/a — report-only under B1 | as E2. Retained for the diagnostic |
| E7 | 5% relative gradient | sometimes (floors 0.005–0.012 relative) | the firm-size earnings gradient is the quantity firm-size policy reads; 5% of the observed large-vs-small gradient is smaller than the gap between adjacent canonical bands, so a passing model preserves band ordering |
| E8 | 0.10 \|log share ratio\| | sometimes (floors 0.05–0.20) | nonemployment incidence drives benefit-eligibility spells; 10% relative error on an age-band incidence is ~1pp at observed levels, below the ASEC-vs-SIPP level disagreement for the same concept |
| E9 j2j | none set | no (floors 0.0766 / 0.0842 dominate) | not needed; floors are non-degenerate |
| E9 stay | **withdrawn** | — | was 100% operative against a degenerate floor with no basis; cell demoted to report-only (§3-E9, B5) |
| B-side thin flag | 10,000 jobs | — | below |

**The 10,000-job thin flag** (§13 item 15's B side, previously "a
draft choice"). Reference calculation: treat a cell's YoY \|log
ratio\| as if the flow count were binomial in the denominator —
`sd ≈ sqrt(2(1-p)/(Np))`. At a typical p ≈ 0.10 separation rate:

| N (jobs) | implied \|log ratio\| sd |
|---|---|
| 2,000 | 0.095 |
| 5,000 | 0.060 |
| **10,000** | **0.042** |
| 20,000 | 0.030 |
| 50,000 | 0.019 |

The measured B-side floors run 0.035–0.097. So at N = 10,000 the
pure count-noise term (0.042) is already the same size as the
smallest floors we measure, and below 10,000 it exceeds them —
meaning the "floor" would be measuring the denominator rather than
the source's temporal stability, which is what it is for.

**Stated honestly**: LEHD cells are noise-infused population
counts, not samples, so this is an order-of-magnitude analogy and
not a derivation. It is offered as the *disclosed basis for a
policy choice*, which is what the campaign rule requires — not as a
sampling result. The A-side 200-person rule has a directly
comparable rationale on the record (Workstream A, 2026-07-17: at
p ≈ 0.5 a 200-person half gives a half-vs-half \|log ratio\| sd
near 0.14).

## 11. The three unit rules (ADR 0003) — IC3 dispositions

1. **QWI/J2J cells count jobs, not persons.** Phase 0 is
   primary-job-only, so person-spells vs job-count cells carry a
   wedge on the order of the multiple-jobholding rate (~5%,
   time-varying). **Disposition (PROPOSED)**: a pre-registered
   jobs/person adjustment factor, published per cell alongside its
   source (CPS multiple-jobholding rate series), applied to E2/E6/E11
   comparisons before scoring. **Scale direction is fixed** by the
   recorded Workstream A decision: inflate person-denominated model
   cells to the job-denominated QWI/J2J scale, never deflate the
   administrative job references to persons. The exact formula,
   series, and vintage remain REFEREE/PENDING in the amendment
   record—an explicit pre-registration item, not a footnote.
2. **QWI publishes mean earnings (`EarnS`), never medians.**
   **Disposition**: E7 stated on means (§3-E7); no median-based
   employer earnings gate exists in the block.
3. **J2J ownership `oslp` vs QWI `op` vs SUSB (no government).**
   NAICS 92 is dropped from the J2J extracts, but state/local
   employment embedded in sectors 61/62 remains. **Unratified
   disposition — REFEREE/PENDING**: carry the scope difference as a
   pre-registered
   per-cell caveat on E2/E11 (the #228 extracts quantify the small
   LED-vs-flat-file margin delta from excluded public "N" flows),
   rather than restating J2J on a private-comparable basis — a
   restatement would require a new extract and re-floor.
   The restatement option stays on the record as the referee
   alternative (§13 item 13).

## 12. Registration and lock ceremony

Per repo convention (gate-1 precedent PR #33/#39; `gate_m6` ceremony
in `docs/design/m6_projection_engine.md`):

1. This document circulates for the **referee round** (adversarial
   review; every §13 item answered on the record).
2. Required pre-lock artifacts land **and are immutable**
   (closes blocking item B3):
   - **PENDING #223**: approved current-head E2 sex×age floor and
     `runs/employer_firm_floors_v1.json`; this branch deliberately
     contains neither.
   - **COMPOSED, not merged/promoted #235**: current draft
     `runs/crosswave_jobid_check_draft_v0.json`. Promotion reconciles
     its internal `draft_v1` label and lands
     `runs/crosswave_jobid_check_v1.json`; this control revision does
     not rename it.
   - **COMPOSED, not merged #236**:
     `docs/design/e4_e5_audit_manifest.md`, registered and undrawn.
   - **COMPOSED, not merged/promoted #274**: byte-faithful
     `runs/seam_reconciliation_draft_v0.json` and builder. The later
     v1 pin/amendment must not rewrite the restored draft anchor.
   - Promotion of the four draft floor artifacts to sha256-pinned
     `v1` with reproduction tests, meeting the M6 byte-reproduction
     standard (pinned builder → byte-identical artifact, zero hand
     edits, reproduction test covering metadata keys) — S5.
   - **COMPOSED, not merged #224**, with the three adopted changes
     folded into `docs/adr/0004-linkage-qc.md`'s text. A locked block
     whose normative ADR exists only as a branch file amended by
     comment thread is not a locked contract.
   - **Every cited evidence PR merged to master** (#212, #223,
     #228, #235, #236, #274) and **every consumed artifact
     sha256-pinned at its merge commit**. The draft's evidence base
     is currently "cited by branch pending merge" over force-pushable
     refs; the round-1 as-reviewed pin list is the record of what
     round 1 saw, and the amendment PR must pin what the *lock*
     sees.
   - **COMPOSED, not merged #277**: the block YAML is authored once
     under final IC1/IC2/IC3 names after that prerequisite merges,
     rather than renamed after being refereed.
2a. **The refereed block YAML** (closes blocking item B2, part 1).
   A committed `docs/design/ic3_employer_gate_block_draft.yaml` —
   enumerated cells for every gate, `derivations` blocks in the
   `tests/test_gates_derivations.py` pattern, the §10.3/§10.4
   partition in machine-checkable form, `locked: false` — is a
   pre-lock artifact, refereed in this round's continuation and
   carried **verbatim with exactly the lock-time deltas** at the
   flip (the gate_m6 precedent, `gates.yaml:5327-5332`). Prose plus
   PROPOSED numbers is not a refereeable block: transcription
   errors, silent cell additions and derivation drift would first
   appear in the amendment PR, unrefereed.

2b. **Referee verification before merge** (B2, part 2). The
   campaign ceremony is draft → adversarial referee → fixes →
   **verification** → ratify-by-merge. M6 ran an explicit referee
   re-check before its flip. §12.3's cross-workstream approval is a
   party check and does not substitute. The amendment PR carries an
   M6-style lock table: builder script commits, artifact sha256s,
   the complete authorized edit surface, and guard tests including
   cell-count mutation pins.

3. A single **amendment PR to `gates.yaml`** adds the employer block
   with referee-resolved numbers, machine-checkable derivations
   (`tests/test_gates_derivations.py` pattern), and `locked: true`;
   authorship by one workstream owner plus approval by the other
   (the ADR 0003 cross-workstream approval norm). Merge of that PR
   is the ratification event; nothing in this draft binds before it.
4. **No one-shot candidate runs before the lock.** Employer-block
   candidates register on issue #42 only after the amendment PR
   merges. Subsequent changes to locked thresholds require a public
   amendment plus a fresh referee round.

## 13. Open questions for the referee round

Every decision this draft leaves to the referee, enumerated:

1. **Threshold policy — REFEREE/PENDING**: set the common or
   gate-specific `k`, and ratify every substantive tolerance in §3.
2. **Temporal-floor basis — REFEREE/PENDING #223**: choose
   ex-pandemic or full-sample floors for E2/E6/E7/E11 margins.
3. **E1 treatment — WORKSTREAM DECISION RECORDED; REFEREE
   VERIFICATION PENDING**: Vahid recorded national coarsened-margin
   and sector report-only treatment. Confirm that disposition and
   the calibrated-margin versus gated-stability partition in §10.
4. **E3 formulation — REFEREE/PENDING**: choose ECDF max-gap or
   quantile gaps and, if needed, a substantive patch for heaping
   zeros. The recorded filename/per-year-cell correction does not
   decide the statistic.
5. **E9 stay formulation — WORKSTREAM DECISION RECORDED; REFEREE
   VERIFICATION PENDING**: Vahid recorded withdrawal of the 0.02
   stay tolerance and report-only treatment for both stay
   statistics. No stay statistic gates unless a later floor and
   substantive basis are approved.
6. **Phase-1 imputed-band adjudicability — WORKSTREAM DECISION
   RECORDED; REFEREE VERIFICATION PENDING**: Vahid recorded the
   permanent person-level report-only disposition and degradation
   ladder in §9.1. The later E12 decision permits only a disjoint,
   aggregate audit of observable grouped margins; it does not
   restore person-level truth or certify worker–firm assignment.
   This item remains numbered for #224 traceability.
7. **Linkage-QC design and numerics — REFEREE/PENDING #236**:
   ratify the pair-level E4 and maximal-run E5 populations,
   `P_floor`, `P_floor_run`, `P_design`, budget/run ceiling,
   arm-specific `q_link`, α, power, multiplicity, whether recall
   gates, repeat-agreement/action rules, and the E4/E5-first scope.
8. **Blinding and draw mechanics — REFEREE/PENDING #236**: approve
   custody, seed commitment, audit-frame freeze, sample draw,
   unblinding order, and immutable evidence publication before any
   audit draw occurs.
9. **Seam ruling — REFEREE/PENDING**: select the operative
   population and correction bands from #235, then ratify or amend
   the J2J-levels / SIPP-persistence / seam-aware interpretation.
10. **E11 scope and floor — REFEREE/PENDING #223**: decide the
    aggregate margin statistic, temporal basis, and threshold.
    Five-quarter detail remains report-only, and no E11 result
    certifies a person-level worker–firm link.
11. **E12 claims boundary — WORKSTREAM DECISION RECORDED; REFEREE
    VERIFICATION PENDING**: Vahid recorded both a future strict
    aggregate audit and deferral of strong linkage/sorting claims.
    The aggregate statistic, disjoint partition, floor, and
    threshold remain REFEREE/PENDING; firm effects, variance,
    sorting, coworker/spillover, and person-level assignment claims
    remain no-go.
12. **Jobs/person scale — DIRECTION RECORDED; DETAILS
    REFEREE/PENDING #212**: job-based QWI/J2J references are not
    deflated. If a person-scale candidate is compared to them, the
    candidate cells are inflated by an approved observed
    jobs-per-person factor. Ratify the exact formula, series,
    vintage, and deployment conversion; #212 is intentionally not
    composed here.
13. **`oslp` versus `op` scope — REFEREE/PENDING**: choose a
    per-cell caveat or private-comparable restatement of the J2J
    references.
14. **Held-out firm-age and state axes — REFEREE/PENDING**: confirm
    report-only registration at first lock and promotion
    conditions.
15. **Thin-cell rules — REFEREE/PENDING #223**: ratify
    `THIN_CELL_PERSONS = 200` for SIPP and the proposed 10,000-job
    B-side minimum denominator.
16. **ASEC reference-period mismatch — REFEREE/PENDING**: confirm
    its treatment as a known label-misalignment note on affected
    cells.
17. **Linkage-bias reweighting — REFEREE/PENDING**: separately
    specify pair- and run-population propensities, overlap and
    balance tolerances, trimming, and audit selection weights.
18. **Operative weighting version — REFEREE/PENDING**: register
    weighted or unweighted E4/E5 as operative, and do the same
    before any later E9/E11/E12 promotion, before candidate scores
    exist.
19. **B1's cost — REFEREE/PENDING**: confirm that first-lock
    firm-side gating rests on E2, E7, and aggregate E11 margins
    only, or direct a registered route to restore firm-side power.
20. **Deployment split/scale — REFEREE/PENDING #212**: ratify the
    conversion from the registered 50/50 half split to the intended
    20% holdout deployment scale, including rounding and strata.
21. **Draft gate block — REFEREE/PENDING**: after every item above
    is answered and every prerequisite is merged at an approved
    digest, approve a separate mechanical YAML amendment. This
    draft does not modify `gates.yaml`, lock IC3, or authorize a
    candidate run.
