# gate_epuf_fill registration: career fills scored on held-out EPUF careers

- **Registration id**: `2026-10-03-epuf-career-fill`
- **Gate**: `gate_epuf_fill` (registered, `locked: false`; not in
  `gates.yaml` until the lock ceremony in section 14 completes)
- **Surface**: the two rules the career assembler
  (`populace_dynamics.estimates.career.build_career`) uses to fill years the
  PSID did not record, and their learned replacements, scored on held-out
  persons of SSA's 2006 Earnings Public-Use File (EPUF).
- **Ceremony stage**: AMENDMENT 1 FLOORS BUILT, awaiting referee round 2.
  Referee round 1 (`reviews/gate_epuf_fill_round1_referee_20261004.md`)
  returned AMEND BEFORE LOCK. This document carries amendment 1 (section
  12), whose floors were rebuilt on DEV at its rules commit (section 10a).
- **What has been seen**:
  - Candidate fills exist and have been scored on DEV against the first
    (v1) floors. Every such score is disclosed in
    `docs/amendments/gate_epuf_fill_dev_scores_before_amendment_1.json`.
  - No TEST person has been read. TEST can be read only through
    `epuf_fill_gate.test_part()`, which refuses until `gates.yaml` locks
    this gate.
- **Code**:
  - `src/populace_dynamics/harness/epuf_fill_gate.py` (the rules);
  - `tests/harness/test_epuf_fill_gate.py`;
  - `scripts/build_epuf_fill_psid_scale.py` (the PSID counts);
  - `scripts/build_epuf_fill_gate_floors.py` (floors, bite, doses,
    oracles);
  - `tests/test_epuf_fill_gate_floors.py` (pins the builds).

## What this gate is, in plain words

A gate here is a pass-or-fail test whose rules and thresholds are fixed and
published before anything is scored against it.

The PSID asked about income only every other year from 1997, and its
earnings panel starts in 1968. The career assembler fills those holes with two
fixed rules:

1. each odd year is the mean of the two years around it; and
2. nothing counts before 1968, or before age 22, whichever is later.

EPUF records capped taxable earnings in every year from 1951 to 2006 for a
1 percent sample of Social Security numbers. So we can hide the years the
PSID would be missing, fill them, and compare the filled careers with the
real ones. This gate does that on persons no fill has seen.

- **Cell pass**: the fill moves the cell by less than the sampling error the
  PSID itself carries there.
- **Gate pass**: the fill passes every cell that gates.

**What a pass certifies, and what it does not.**
- It certifies a fill on EPUF's administrative, capped, disclosure-processed
  earnings.
- In use, the years a fill conditions on are PSID survey reports of
  uncapped labour income, converted to a share of the wage base. The gate
  does not measure the gap between the two sources. PR #509's registration
  reports that gap.

Max approved the direction on 2026-10-03: "at a minimum seems like we could
use it to improve the odd-year filling, we're overstating that form of
persistence with our current method".

## 1. Data

- **Source**: EPUF 2006 (`populace_dynamics.data.epuf`, SHA-256-pinned, from
  PR #509).
  - 4,384,254 persons.
  - Capped taxable earnings 1951-2006, after SSA's disclosure operator.
  - Sex and year of birth; no family links, deaths or migration.
  - Capped earnings are the AIME's concept.
- **Reading** (`epuf_fill_gate.epuf_matrix`):
  - Every annual row must join one demographic person, once per year.
  - TRAIN and DEV are read directly. TEST is read only through `test_part()`
    after lock.
- **Persons**: sex coded 1 or 2. 3,054 persons with unspecified sex are
  dropped.
- **Wage bases**: EPUF's own (`epuf_operator.wage_base`).
- **NAWI**: `cola_track_a.statutory.captured_ssa_parameters().nawi`.
- **PSID scale**: the default-spec PSID-2010 cohort
  (`cohorts.psid2010.build_psid2010_cohort`), 11,405 members. Its counts are
  in `runs/epuf_fill_gate_psid_scale_v2.json` (section 5).

## 2. Split

Each person's position `u` in [0, 1) is computed by
`epuf_fill_gate.split_part`:

1. take SHA-256 of `populace_dynamics.epuf_fill.split.v1|` followed by the
   decimal person id;
2. read the first eight bytes, big-endian;
3. divide by 2^64.

| Part | Rule | Persons | Use |
|---|---|---:|---|
| TRAIN | u < 0.6 | 2,629,944 | Fills learn from it; exploration; dry runs |
| DEV | 0.6 <= u < 0.8 | 875,829 | Floors, checks on bite, doses, oracles; candidate development |
| TEST | u >= 0.8 | 878,481 | Read once, through `test_part()`, after lock |

- The split was fixed before any EPUF statistic was computed in this work.
- The counts include persons of unspecified sex.

## 3. Masks, and what a fill is given

Two families of years, as the PSID would leave a career:

- **`odd`**: the odd years 1997, 1999, 2001, 2003 and 2005. The assembler
  also fills 2007-2011 and the 2013 seam, which lie past EPUF's last year.
- **`pre`**: every year from 1951 before `max(1968, birth_year + 22)`.
  - For cohorts born 1930-1945 this is 1951-1967.
  - For cohorts born 1946-1980 it is every year before age 22.
  - EPUF has no earnings below age 15 for cohorts born after 1937.

**The scoring path** (`epuf_fill_gate.score_candidate`):
1. Every fill is given shares of the wage base with **both families' cells
   unknown** (NaN), together with each person's sex, year of birth and id.
2. It fills its own family's cells.
3. Each draw must return finite shares in [0, 1] on those cells and leave
   every other cell exactly as given; otherwise `FillOutputInvalid` is
   raised.
4. A share of 1 becomes exactly the wage base.
5. The filled cells replace the truth's cells of the fill's own family, and
   every other cell stays true. The other family's cells are therefore true
   when a family is scored, but unknown to its fill.

## 4. Cells

### 4.1 Groups and populations

- Every cell belongs to one **floor group**, `<family>.<sex>.<stratum>`
  (`group_of`). There are 40 groups (`groups()`).
- `group_rows(group)` defines exactly the persons a group's cells count.
  The cells and the floors (section 5) both take their persons from it.
- Populations read no cell their own family masks:
  - `odd` universe: positive in a recorded even year 1996-2006.
  - `odd_career` universe: positive in a year from
    `max(1968, birth_year + 22)` through 2006 that is not a masked odd year.
  - `pre` universe: positive in a year from `max(1968, birth_year + 22)`
    through 2006.
- Within a population, some denominators read the masked year itself:
  `atcap` (positive at `t`), the quantiles of positive shares, and every
  "positive in both years" correlation. A fill that gets the zero rate
  wrong therefore also moves those cells.

### 4.2 Family `odd`

**Age-band groups** (`odd.<sex>.<band>`):
- Bands: 22-29, 30-44, 45-59, 60-74, and 22-74, which pools the four.
- The assembler fills odd years only inside the career, so units start at
  age 22.
- Population: `odd` universe members with a masked odd year at an age in
  the band.
- Units: their person-years at a masked year `t` at an age in the band.

| Statistic | Definition | Scale |
|---|---|---|
| `r1` | Spearman of `t` with `t-1` and with `t+1`, positive in both; mean of the pairs | gap |
| `r3` | Spearman of `t` with `t-3` and with `t+3` (recorded), positive in both; mean | gap |
| `r2`, `r4` | Spearman of `t` with `t+2` / `t+4` (both masked), positive in both; mean | gap |
| `zint` | Share zero at `t`, among units positive at `t-1` and `t+1` | log ratio |
| `zexit` | Share zero at `t`, among units positive at exactly one of them | log ratio |
| `wint` | Share positive at `t`, among units zero at both | log ratio |
| `atcap` | Share at the wage base, among units positive at `t` | log ratio |
| `level` | Mean share of the wage base at `t`, zeros included | log ratio |
| `q10`, `q50`, `q90` | Quantiles of the positive shares at `t` | log ratio |

**Cohort groups** (population: `odd_career` universe members of the cohort):
- **Born 1936-1940, 1941-1945, and 1936-1945 pooled**: `aime_p10`, `p25`,
  `p50`, `p75` and `p90`, the percentiles of the AIME under the 35-year rule
  through age 61 (`aime_35`). A Hypothesis test pins `aime_35` to
  `ss.statutory_aime.aime`.
- **Born 1946-1955, 1956-1965, 1966-1980, and 1946-1980 pooled**: the same
  percentiles of the **partial AIME** (`partial_aime`).
  - It is the AIME formula applied to every year through 2006, indexed to
    NAWI in 2006.
  - It is not a statutory AIME. It measures how a fill moves the AIME's
    ingredients for cohorts EPUF cannot follow to 61.

### 4.3 Family `pre`

Population: `pre` universe members of the cohort.

**Born 1930-1934, 1935-1939, 1940-1945, and 1930-1945 pooled** (masked
years 1951-1967):

| Statistic | Definition |
|---|---|
| `aime_p10` to `aime_p90` | Percentiles of the AIME |
| `pzero` | Share of masked person-years at ages 18 and over with no earnings |
| `plevel` | Mean share of the wage base in those person-years |
| `pr_in` | Spearman of 1962 with 1967 (both masked) |
| `pr_cross` | Spearman of 1965 (masked) with 1970 (recorded) |

**Born 1946-1955, 1956-1965, 1966-1980, and 1946-1980 pooled** (masked
years: ages 21 and under):

| Statistic | Definition |
|---|---|
| `yzero` | Share of person-years at ages 15-21 with no earnings |
| `ylevel` | Mean share of the wage base at ages 15-21 |
| `yr_cross` | Spearman of earnings at age 21 with earnings at age 24 |
| `paime_p10` to `paime_p90` | Percentiles of the partial AIME |

Every correlation is computed among persons positive in both years.

**Pooled groups.** A fill whose bias is just inside the tolerance in every
cohort or band, all in the same direction, would bias a pooled PSID
estimate by more than the pooled estimate's own sampling error. The pooled
groups gate that bias directly, with floors at the pooled PSID size.

There are 326 cells in all.

## 5. Gap, floor and tolerance

**Gap** (`gap`):
- For a correlation, the filled value minus the true value.
- For every other cell, the log of the filled value over the true value.
- A candidate's filled value is the mean of the cell over the 20 draw seeds
  `DRAW_SEEDS = 7100..7119`. Its gap is the gap of that mean (`score`).

**Floor** (`floor_group`):
- Each of `N_FLOOR_REPLICATES = 200` replicates draws two disjoint samples
  of `n` persons from the group's DEV population (`group_rows`). It uses
  the stream `default_rng([5000, group index, 200, n])`, where the group
  index is the group's position in `groups()`.
- It computes every cell on both samples and records
  `[m(A) - m(B)] / sqrt(2)` on the cell's scale.
- The cell's `sigma` is the root mean square of its replicates. For two
  independent samples that estimates one sample's standard error: the
  sampling error a PSID-sized sample carries in that cell.

**Sample size `n`** (from `runs/epuf_fill_gate_psid_scale_v2.json`):
- **Age-band groups**: the number of PSID-2010 career years the assembler
  filled with the neighbour mean at an age in the band, among members
  positive in a recorded even year 1996-2010. This is divided by the mean
  number of masked units per DEV population member in the band, so a sample
  carries about as many masked units as the PSID fills.
- **Cohort groups**: the number of PSID-2010 members of that sex and cohort
  who are positive in a recorded year from `max(1968, birth_year + 22)`
  through 2010.
- The counts are unweighted. Several things make the floors narrower than
  the PSID's real sampling error, and so make the gate stricter on
  balance:
  - the PSID's effective sample size is below its count;
  - its persons are clustered in families;
  - its filled-year count includes 2007-2011 and the 2013 seam.

  Matching units rather than persons works slightly the other way in some
  bands.

**Tolerance**: `tau = K * sigma` with `K = 1`. A gating cell passes if its
gap is finite and `|gap| <= tau`.

**What K = 1 means.** The tolerance is a **materiality threshold**:
- Suppose a fill's bias in a cell equals one PSID standard error. Then the
  root mean square error of a PSID-sized estimate built on the fill is at
  most the square root of 2 times the PSID's own sampling error.
- A fill within the tolerance is never the larger source of error in that
  cell. The pooled groups extend that to estimates pooled across cohorts or
  bands.
- The comparison's own noise is much smaller than `tau` (see the operating
  characteristic below). So this is not, in the sense other gates use,
  "the noise of the comparison".
- Max's ratification of this reading is queued (section 14).

**Operating characteristic**:
- The gap compares the truth and the fill on the same TEST persons, so it
  carries no error from which persons were sampled.
- A fill that draws from the true conditional law has a gap whose standard
  deviation is at most about `sqrt(1 + 1/20) * sqrt(n / N) * sigma`. Here
  `N` is the group's population on a part, and the stored `noise_ratio` is
  `sqrt(n / N)`.
- The verdict is therefore close to a step at `|bias| = sigma`. With some
  300 gating cells, a faithful fill fails one by chance with negligible
  probability. A fill whose bias in a cell is near `sigma` can land on
  either side of it.

## 6. Which cells gate, and the checks before lock

A cell gates (`partition`) if, on DEV, all of these hold:
1. its true value is finite, and positive for a log-ratio cell;
2. its floor `sigma` is finite and positive;
3. in at least 95 percent of floor replicates, the smaller sample of the
   pair has at least 20 events. A share's events are the smaller of its
   hits and misses; a correlation's are the pairs in its smallest pair-year;
   a quantile's are the positive values behind it.

Every other cell is reported without a verdict. The partition is fixed at
the floor build and recorded in the artifact.

**Bite.** Before lock, on DEV:
- **B1**: the current odd-year rule must fail at least one gating `odd`
  cell by more than `2 * tau`.
- **B2**: the current pre-career rule must fail at least one gating `pre`
  cell by more than `2 * tau`.

If either check fails, the gate does not lock.

**Dosed perturbations** (report-only). These are perturbations of the true
DEV matrix. Each is scored, its gaps are reported in tolerances, and the
dosed ones report the dose at which the most sensitive cell reaches one and
two tolerances.

| Id | Family | Perturbation | What it tests |
|---|---|---|---|
| D1 | `odd` | Copy `t+1` into `t` | Copying a neighbour |
| D2 | `odd` | Permute `t` within sex and five-year age band | The marginal law |
| D3 | `odd` | Shrink positive log shares toward their stratum median by `lambda` = 0.75 and 0.5 | Dispersion |
| D4 | `pre` | Scale the true blocks by 0.95 and 0.90 | Level bias in the AIME and `plevel` |
| D5 | `pre` | Permute whole blocks within sex and birth year only | Matching |
| D6 | `pre` | Permute each masked year independently within sex and birth year | Persistence |

**Oracles** (report-only). Two fills permute true values among similar DEV
persons, over `ORACLE_SEEDS = 7200..7219`. Each conditions only on what a
fill is given:
- **O1** (`odd_oracle_fill`) permutes the true value of each masked odd year
  among persons who share all of: sex; `odd` universe membership; five-year
  age band at `t`; and the bins of `t-1` and `t+1`. A neighbour inside the
  pre-career mask counts as unknown.
- **O2** (`pre_career_oracle_fill`) permutes whole masked blocks among
  persons who share all of: sex; birth year; `pre` universe membership; the
  number of positive years among the first five recorded years (a masked
  odd year is unknown); and the quintile of their mean share.

## 7. Candidates

Each family has a primary candidate and a registered alternative.
- All four are fitted on TRAIN only and developed against DEV.
- Each is registered with its code commit and the SHA-256 of its fitted
  artifact before TEST is read. **The registered commit and SHA-256
  govern.** The descriptions below are summaries.
- Every candidate produces shares in [0, 1] through the scoring path of
  section 3. Its draws come from counter-based uniforms keyed by the fill,
  the draw seed, the person id and the year, so a person's draw does not
  depend on which other persons are filled.

### 7.1 Odd years

**Primary: a two-part conditional draw (QRF-style).**
- It draws the share of the wage base at `t`: a probability of a zero year,
  then conditional quantiles of a positive share.
- It conditions on the recorded shares around `t` (`t-1`, `t+1`, `t-3`,
  `t+3` and further where recorded), sex and age.
- A copula across a person's masked years carries the dependence the
  conditioning leaves.

**Alternative: kNN triples.** It draws the share at `t` from one of the `k`
nearest TRAIN person-years in the shares at `t-1` and `t+1`, sex and age.

### 7.2 Pre-career years

**Primary: rank-kNN donor careers.**
- **Donor pool**: TRAIN persons of the same sex and birth year who are in
  the `pre` universe.
- **Match vector**: a person's percentile rank within the donor pool in the
  first five years from their career start that they have recorded.
- **Draw**: one of the `k` nearest donors is chosen by the seeded uniform,
  and the whole masked block is copied from that donor.
- **Precedent**: gate 1's passing candidate was rank-kNN
  (`runs/gate1_rank_knn_v5.json`: 10-year autocorrelation 0.499-0.533
  against a reference of 0.539).

**Alternative: a chained one-sided fill.** It draws year `y` from year
`y+1`, sex and age, working backward from the career start.
- Gate 1's chained weighted QRF baseline failed long persistence
  (`runs/gate1_qrf_baseline_v1.json`: 10-year autocorrelation 0.309-0.368
  against 0.539, tolerance 0.07).
- This alternative is registered so that the choice of borrowing whole
  careers is tested rather than assumed.

### 7.3 Adoption rule

This rule is coded in `adoption_tier` and `adopt`. Each candidate and the
current rule are scored on the same TEST persons. A candidate's tier is:
- **certified** if it passes the gate;
- **improves** if it fails the gate but meets both of these:
  - in every gating cell its gap is finite and at most
    `max(tau, min(|current gap|, 3 * tau))`, where a non-finite current gap
    counts as infinite;
  - it fails strictly fewer gating cells than the current rule;
- **not adopted** otherwise.

In each family, the candidate in the better tier is adopted, and the
primary is adopted on a tie. If both are not adopted, the current rule
stays.
- An adopted candidate in the **improves** tier is recorded as an
  uncertified improvement, and no text may call it certified.
- The cap of three tolerances (amendment 1) means "improves" requires a
  fill to be near the tolerance everywhere, not merely finite where the
  current rule is not.

## 8. Implementation behind the rule

- `estimates/career.py` stays byte-identical. The first-estimates
  birth-evidence reducer seals every file under `src/` against its reviewed
  commit (`scripts/first_estimates_birth_evidence.py`,
  `_assert_input_identity`), and `career.py` is reachable from it.
- The gate's rules module, `harness/epuf_fill_gate.py`, is listed in the
  reducer's `POST_REVIEW_SOURCE_EXCLUSIONS`, and a test proves it is
  unreachable from the reducer.
- The candidate fills will live in a new opt-in module under the same
  exclusion. Its provenance values are `gap_epuf_drawn` and
  `pre_career_epuf_donor`, so a year's provenance always names the rule
  that produced it.
- `cohorts/psid2010.py`, which is outside the seal, gains a spec field for
  the fill. Its default stays the current rule until a new registration of
  the DYNASIM projections adopts the learned fills (section 11).

## 9. Evidence before the first floor build

**TRAIN exploration** of the current rules and of conditional-permutation
oracles. None of it fitted a candidate, built a DEV floor or read a TEST
person.

The current odd-year rule:
- raises `r1` by 0.047-0.103 and `r2` by 0.068-0.157;
- removes every zero year where a career starts or stops (`zexit`: true
  0.39-0.52, filled 0);
- removes every zero year between two working years (`zint`: true
  0.016-0.037, filled 0);
- moves the median AIME of the 1936-1945 cohorts by 0.2 percent or less.

The conditional-permutation oracles:
- One conditioning on `t-1` and `t+1` only understates `r2` by 0.006-0.032.
- Adding `t-3` and `t+3` cuts that to 0.001-0.015.

On DEV, the current pre-career rule lowers the pre-universe median AIME
(log gaps from the v1 artifact, converted to percent):

| Cohort | Men | Women |
|---|---:|---:|
| 1930-1934 | 32% | 34% |
| 1935-1939 | 20% | 25% |
| 1940-1945 | 8% | 13% |

Zeroing only the years before age 22 lowers median AIME by 2-3 percent for
men and 7-11 percent for women born 1930-1945 (TRAIN, all persons of the
cohort). The PSID-2010 cohort's members born 1946 or later lose those years
under the current rule. That is why family `pre` covers every year before
`max(1968, birth_year + 22)`, not only 1951-1967.

## 10. The first build (v1), superseded

`runs/epuf_fill_gate_floors_v1.json` (built once on DEV at `d21aa659`) is
frozen. Referee round 1 found that four of its groups were priced on the
wrong population, among other findings (section 12).
- Under v1's rules, 130 of 136 cells gated.
- B1 failed 48 of 70 gating `odd` cells by more than two tolerances, and B2
  failed 54 of 60 gating `pre` cells.
- O1 failed 16 cells: seven of eight `r2` cells, six `r4` cells, and three
  young-band `wint`/`zexit` cells.
- O2 failed 4 `yr_cross` cells, each by under 1.2 tolerances.
- `tests/test_epuf_fill_gate_floors.py` keeps v1 internally consistent.

### 10a. Results of the amended (v2) build

The registered v2 build ran once on DEV at `23bee82c`: the amendment-1
rules commit `7061200d` plus the v2 PSID counts. It is
`runs/epuf_fill_gate_floors_v2.json`.

**Partition**: 319 of 326 cells gate. Seven are report-only:
- too few events: `wint` for men 22-29, men 60-74 and women 60-74;
  `atcap` for women 22-29 and 60-74; `zint` for women 60-74;
- undefined floor: `odd.men.a45_59.q90`. Men's 90th-percentile positive
  share is the cap in every sample, so its sampling error is zero.

**Tolerances** (`K * sigma`) range by statistic:

| Statistic | Tolerance | Statistic | Tolerance |
|---|---|---|---|
| `r1` | 0.0025-0.0098 | `aime_p50` | 0.042-0.125 (log) |
| `r2` | 0.0046-0.0222 | `paime_p50` | 0.021-0.043 (log) |
| `r3` | 0.0047-0.0206 | `pzero` | 0.029-0.129 (log) |
| `r4` | 0.0070-0.0382 | `plevel` | 0.029-0.094 (log) |
| `zint` | 0.045-0.178 (log) | `pr_in` | 0.041-0.133 |
| `zexit` | 0.016-0.052 (log) | `pr_cross` | 0.044-0.122 |
| `wint` | 0.071-0.150 (log) | `yzero` | 0.009-0.023 (log) |
| `level` | 0.011-0.052 (log) | `ylevel` | 0.015-0.030 (log) |
| `q50` | 0.012-0.075 (log) | `yr_cross` | 0.015-0.037 |

The noise ratio `sqrt(n / N)` runs from 0.087 to 0.212.

**Bite: both checks hold, so the gate can lock.**
- **B1**, the current odd-year rule, fails 97 of 183 gating `odd` cells by
  more than two tolerances.
- **B2**, the current pre-career rule, fails 112 of 136 gating `pre` cells
  by more than two tolerances.
- On the pooled 1930-1945 cohorts, B2 lowers the median AIME by 20 percent
  for men (5.3 tolerances) and 22 percent for women (4.0 tolerances).
- On the single cohorts the falls are:

| Cohort | Men | Women |
|---|---:|---:|
| 1930-1934 | 32% | 34% |
| 1935-1939 | 20% | 25% |
| 1940-1945 | 8% | 13% |

**Dosed perturbations** (report-only; number of gating cells failed, and
failed by more than two tolerances):

| Perturbation | Failed | Beyond 2 tol. |
|---|---:|---:|
| D1 copy `t+1` | 92 / 183 | 63 |
| D2 marginal draws | 127 / 183 | 115 |
| D3 shrink, lambda 0.75 | 56 / 183 | 37 |
| D3 shrink, lambda 0.5 | 81 / 183 | 63 |
| D4 scale pre blocks by 0.95 | 12 / 136 | 5 |
| D4 scale pre blocks by 0.90 | 16 / 136 | 12 |
| D5 blocks permuted within sex and birth year | 75 / 136 | 54 |
| D6 pre years permuted independently | 83 / 136 | 61 |

- A pre-career level bias of 1.4 percent moves the most sensitive cell one
  tolerance, and 2.9 percent moves it two.
- A dispersion shrink of `lambda` = 0.996 moves one cell one tolerance. That
  cell is `atcap`: any shrink takes values off the cap.

**Oracles** (report-only):
- **O1** fails 32 of 183 gating `odd` cells: 8 `r2`, 10 `r4`, 9 `r3`, 3
  `r1`, 1 `wint` and 1 `zint`. Conditioning on `t-1` and `t+1` alone misses
  multi-year persistence.
- **O2** fails 6 of 136 gating `pre` cells: 5 `yr_cross` and 1 `aime_p10`.

## 11. What changes downstream

- The DYNASIM projection comparisons (registered one-shot benchmarks) build
  their cohort with `cohorts.psid2010`, so their AIMEs inherit the fill.
  Adopting a learned fill for them needs a new registration and a new run,
  not a silent rerun. That decision is queued for Max.
- The first-estimates path (`build_career_inclusion`) is sealed historical
  evidence and keeps the current rule.

## 12. Amendment 1: referee round 1 and the response

Round 1 (`reviews/gate_epuf_fill_round1_referee_20261004.md`, an
independent Opus 5.5 lane) returned AMEND BEFORE LOCK.

Before amending, every DEV score of a candidate produced so far was
committed: `docs/amendments/gate_epuf_fill_dev_scores_before_amendment_1.json`.
Five scoring events:
- an odd-year primary at 29 and then 26 of 70 cells failing;
- the kNN alternative at 24 of 70;
- the donor primary at 1 of 60, after a first run that stopped on unfilled
  cells.

Every amendment below is justified on the truth side. None loosens a cell
those scores failed.

| # | Finding | Response |
|---|---|---|
| 1 | Odd AIME floors priced on the wrong population | `group_rows` defines each group's population once; cells and floors both use it; a test checks every group's count |
| 2 | The 18-29 band scored ages 18-21, which the assembler never fills with the mean | Odd units start at 22; the band is `a22_29` |
| 3 | Same-direction bias across cells unchecked | Pooled groups (bands 22-74; cohorts 1936-45, 1930-45, 1946-80) at pooled PSID size; AIME p10 and p90 |
| 4 | The pre fill read true odd years | Every fill is given the union of both masks as unknown (section 3) |
| 5 | No registered scoring path or validity checks | `score_candidate` with `FillOutputInvalid`; TEST only through `test_part()` after lock |
| 6 | "Improves" nearly vacuous where the current gap is infinite | The allowance is capped at three tolerances |
| 7 | Candidates existed contrary to the record | Disclosed; this header corrected; section 7 defers to the registered commit and SHA-256 |
| 8 | Bite only through degenerate failures | Dosed perturbations D1-D6, reported with doses at one and two tolerances |
| 9 | Unmeasured modes | `r3` (masked to recorded at ±3); positive-share quantiles `q10`/`q50`/`q90`; partial AIME for cohorts born 1946-1980 |
| 10 | Claims | Universes and denominators reworded (section 4.1); AIME table in percent from DEV (section 9); infinite and NaN gaps distinguished; scope sentence added |
| 11 | "Conservative" sample size | Restated as stricter on balance (section 5) |
| 12 | Tolerance as materiality; house formula on full-DEV halves | Recorded in sections 5 and 13; Max's ratification queued |
| 13 | `epuf_matrix` join and `atcap` exactness | Join asserted; a share of 1 becomes exactly the wage base |
| 14 | Dry-run provenance | `runs/epuf_fill_gate_floors_train_dryrun_v0.json` committed. It was built from the uncommitted working tree when HEAD was `61ade83a`, an ancestor of the rules commit `14045be4`, before universe membership in the oracle strata and the improves tier were added |
| 15 | Tests | Added: each group counts exactly its rows; populations invariant to their family's mask; units from age 22; scoring-path validity and union-mask inputs; refused TEST reads; the EPUF join |

**Forks ledger** (rules changed after a floor build or a candidate score):

| Change | Seen before it | Why it is not a self-rescue |
|---|---|---|
| Oracle strata gain universe membership | TRAIN dry run | Oracles are report-only |
| "Improves" tier added | TRAIN dry run (an oracle failing `r2`/`r4`) | Adoption only; no certification changes |
| Amendment 1 (all of the above) | v1 DEV floors; candidate DEV scores (disclosed) | Every change comes from referee round 1 and is truth-side. It adds cells and pooled groups, tightens adoption, and removes units the PSID does not fill |

## 13. Considered and rejected

1. **Floors from two halves of all DEV persons, and the house tolerance
   `round(mean |e| + 4 sd |e|, 3)` on them.**
   - With same-person scoring, the house formula on full-DEV halves gives a
     tolerance of roughly `4.5 * sqrt(2n / N) * sigma`, about 0.55-1.35
     sigma here. That is the same order as `K = 1`, and it is tied to the
     comparison's real noise.
   - The registered tolerance instead prices materiality at the PSID's
     size, which matches the house's deployment-scale floor (`gates.yaml`
     noise-floor notes).
   - The two readings agree in order. This registration takes the
     materiality reading and asks Max to ratify it.
2. **Halves of all DEV persons with `K = 1`.** Each half would have about
   440,000 persons. The gate would demand a fitted model's bias fall below
   noise no PSID-based estimate can perceive.
3. **Scoring the fill by its AIME alone.** On EPUF the current odd-year
   rule moves the median AIME by 0.2 percent or less while distorting
   persistence and zero years badly.
4. **Masking only 1951-1967.** It would leave untested the age-22 part of
   the rule, which lowers AIME for every PSID-2010 member born after 1945.
5. **Weighting the PSID counts.** Effective sample sizes would loosen the
   floors.
6. **A sign rule over cells** (the mean standardized gap over a
   statistic's cells within `1/sqrt(k)`). Pooled groups do the same job
   with ordinary cells and floors.

## 14. Ceremony checklist

- [x] Rules pushed before any DEV floor (`14045be4`)
- [x] PSID scale counts v1 and floor build v1 on DEV (superseded)
- [x] Adversarial referee round 1: AMEND BEFORE LOCK
- [x] DEV candidate scores disclosed before amending
- [x] Amendment 1 rules (this document, the code and tests) pushed before
  the v2 floor build
- [x] PSID scale counts v2 and floor build v2 on DEV (`23bee82c`);
  lockable
- [ ] Referee round 2 (verification)
- [ ] Max ratifies the materiality reading of the tolerance (queued
  decision)
- [ ] Ratifying merge; lock flip in `gates.yaml`
- [ ] Candidates registered (code commit, fitted-artifact SHA-256)
- [ ] TEST read through `test_part()` and scored once; result published
  whether it passes or fails
