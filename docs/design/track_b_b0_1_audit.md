# Track B B0.1: source, exposure, access and power audit for B2

**Status: protocol frozen; counts not yet run.** This commit freezes the
structural-audit protocol that design §5.2 requires before any count or
power summary is computed. The audit's findings are added in a later
commit, after the count script below has run once on staged data.

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
