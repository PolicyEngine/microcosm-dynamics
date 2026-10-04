# gate_epuf_fill registration: career fills scored on held-out EPUF careers

- **Registration id**: `2026-10-03-epuf-career-fill`
- **Gate**: `gate_epuf_fill` (registered, `locked: false`; not in
  `gates.yaml` until the lock ceremony in section 12 completes)
- **Surface**: the two rules the career assembler
  (`populace_dynamics.estimates.career.build_career`) uses to fill years the
  PSID did not record, and their learned replacements, scored on held-out
  persons of SSA's 2006 Earnings Public-Use File (EPUF).
- **Ceremony stage**: RULES. No DEV floor has been built, no candidate has
  been fitted, and no TEST person has been read.
- **Code**: `src/populace_dynamics/harness/epuf_fill_gate.py` (split, masks,
  current rules, cells, floors, partition, scoring, adoption, oracles),
  `tests/harness/test_epuf_fill_gate.py`,
  `scripts/build_epuf_fill_psid_scale.py` (PSID counts) and
  `scripts/build_epuf_fill_gate_floors.py` (floors, bite, oracles).

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
- **Persons**: sex coded 1 or 2. 3,054 persons with unspecified sex are
  dropped.
- **Wage bases**: EPUF's own (`epuf_operator.wage_base`).
- **NAWI**: `cola_track_a.statutory.captured_ssa_parameters().nawi`.
- **PSID scale**: the default-spec PSID-2010 cohort
  (`cohorts.psid2010.build_psid2010_cohort`), 11,405 members. Its counts are
  in `runs/epuf_fill_gate_psid_scale_v1.json` (section 5).

## 2. Split

Each person's position `u` in [0, 1) is computed by
`epuf_fill_gate.split_part`:

1. take SHA-256 of `populace_dynamics.epuf_fill.split.v1|` followed by the
   decimal person id;
2. read the first eight bytes, big-endian;
3. divide by 2^64.

| Part | Rule | Persons | Use |
|---|---|---:|---|
| TRAIN | u < 0.6 | 2,629,944 | Fills learn from it; exploration of the current rules; dry runs |
| DEV | 0.6 <= u < 0.8 | 875,829 | Floors, the checks on bite, the oracles; candidate development |
| TEST | u >= 0.8 | 878,481 | Scored once per registered candidate, after lock |

- The split was fixed before any EPUF statistic was computed in this work.
- The counts include persons of unspecified sex.

## 3. Masks

Two families of years are masked separately, as the PSID would leave a
career.

- **`odd`**: the odd years 1997, 1999, 2001, 2003 and 2005. The assembler
  also fills 2007-2011 and the 2013 seam, which lie past EPUF's last year.
- **`pre`**: every year from 1951 before `max(1968, birth_year + 22)`.
  - For cohorts born 1930-1945 this is 1951-1967.
  - For cohorts born 1946-1980 it is every year before age 22.
  - EPUF has no earnings below age 15 for cohorts born after 1937.

A fill sees every unmasked year of the person, their sex and their year of
birth, and nothing else.

## 4. Cells

Every cell is computed by one function (`odd_cells` or `pre_career_cells`)
on the true matrix and on the filled matrix of the same persons. No
universe or conditioning denominator reads a masked year. So the true and
filled matrices share every universe, and every set of units defined by
recorded neighbours.

### 4.1 Family `odd`

**Universe** (`family_universe`): persons with positive earnings in at
least one recorded even year from 1996 to 2006.

**Units**: person-years at a masked year `t`. They are stratified by sex
and by age at `t`, in four bands: 18-29, 30-44, 45-59 and 60-74.

| Statistic | Definition | Scale |
|---|---|---|
| `r1` | Spearman correlation of `t` with `t-1`, and of `t` with `t+1`, among units positive in both years. Mean of the ten pairs | gap |
| `r2` | Spearman correlation of `t` with `t+2` (both masked), positive in both. Mean of four pairs | gap |
| `r4` | Spearman correlation of `t` with `t+4` (both masked), positive in both. Mean of three pairs | gap |
| `zint` | Share zero at `t`, among units positive at both `t-1` and `t+1` | log ratio |
| `zexit` | Share zero at `t`, among units positive at exactly one of `t-1` and `t+1` | log ratio |
| `wint` | Share positive at `t`, among units zero at both `t-1` and `t+1` | log ratio |
| `atcap` | Share at the wage base, among units positive at `t` | log ratio |
| `level` | Mean of earnings over the wage base at `t`, zeros included | log ratio |

**Career cells** cover men and women born 1936-1940 and 1941-1945, within
the universe:
- `aime_p25`, `aime_p50` and `aime_p75` are the quartiles of the AIME under
  the 35-year rule through age 61 (`aime_35`).
- A Hypothesis test pins `aime_35` to `ss.statutory_aime.aime`.
- For these cohorts the AIME window includes masked odd years.

### 4.2 Family `pre`

**Universe**: persons with positive earnings in at least one year from
`max(1968, birth_year + 22)` through 2006.

**Men and women born 1930-1934, 1935-1939 and 1940-1945.** For them the
masked years are 1951-1967.

| Statistic | Definition |
|---|---|
| `aime_p25`, `aime_p50`, `aime_p75` | Quartiles of the AIME |
| `pzero` | Share of masked person-years at ages 18 and over with no earnings |
| `plevel` | Mean earnings over the wage base in those person-years |
| `pr_in` | Spearman correlation of 1962 with 1967 (both masked) |
| `pr_cross` | Spearman correlation of 1965 (masked) with 1970 (recorded) |

**Men and women born 1946-1955, 1956-1965 and 1966-1980.** For them the
masked years are ages 21 and under.

| Statistic | Definition |
|---|---|
| `yzero` | Share of person-years at ages 15-21 with no earnings |
| `ylevel` | Mean earnings over the wage base at ages 15-21 |
| `yr_cross` | Spearman correlation of earnings at age 21 with earnings at age 24 |

Every correlation is computed among persons positive in both years.

There are 136 cells in all: 64 odd-year cells, 12 odd-family AIME cells
and 60 `pre` cells.

## 5. Gap, floor and tolerance

**Gap** (`gap`):
- For a correlation, the filled value minus the true value.
- For every other cell, the log of the filled value over the true value.
- A candidate's filled value is the mean of the cell over the 20 draw seeds
  `DRAW_SEEDS = 7100..7119`. Its gap is the gap of that mean (`score`).

**Floor groups**:
- A cell's floor group is its id without the statistic (`group_of`). For
  example, the seven statistics of `odd.men.a30_44` form one group, and the
  three AIME quartiles of `pre.women.b1930_1934` form another.
- The cells of a group share one pool and one sample size. There are 24
  groups.
- **Pool** (`group_eligible`): DEV universe members of the group's sex who
  have a masked odd year at an age in the band (age-band groups), or who
  were born in the cohort (cohort groups).

**Sample size** (the PSID's size, from
`runs/epuf_fill_gate_psid_scale_v1.json`):
- **Age-band groups**: the number of PSID-2010 career years the assembler
  filled with the neighbour mean at an age in the band, among members
  positive in a recorded even year 1996-2010. This is divided by the mean
  number of masked units per DEV pool member in the band, so a sample
  carries about as many masked units as the PSID fills.
- **Cohort groups**: the number of PSID-2010 members of that sex and cohort
  who are positive in a recorded year from `max(1968, birth_year + 22)`
  through 2010.
- The counts are unweighted. The PSID's effective sample size is smaller
  than its count, so a floor built on the count is narrower than the PSID's
  real sampling error, and the gate is stricter.

| Group | PSID units | Group | PSID members |
|---|---:|---|---:|
| odd men 18-29 | 3,949 years | odd men 1936-40, 1941-45 | 145, 244 |
| odd men 30-44 | 11,148 | odd women 1936-40, 1941-45 | 161, 232 |
| odd men 45-59 | 9,472 | pre men 1930-34, 35-39, 40-45 | 92, 131, 278 |
| odd men 60-74 | 2,670 | pre women 1930-34, 35-39, 40-45 | 153, 149, 270 |
| odd women 18-29 | 5,318 | pre men 1946-55, 56-65, 66-80 | 1,036, 1,159, 1,993 |
| odd women 30-44 | 13,927 | pre women 1946-55, 56-65, 66-80 | 1,136, 1,504, 2,296 |
| odd women 45-59 | 10,663 | | |
| odd women 60-74 | 2,773 | | |

**Floor** (`floor_group`):
- Each of `N_FLOOR_REPLICATES = 200` replicates draws two disjoint samples
  of that size from the group's DEV pool. It uses the stream
  `default_rng([5000, group index, 200, n])`, where the group index is the
  group's position in the sorted list of group ids.
- It computes every cell on both samples and records
  `[m(A) - m(B)] / sqrt(2)` on the cell's scale.
- The cell's `sigma` is the root mean square of its replicates. For two
  independent samples that estimates one sample's standard error: the
  sampling error a PSID-sized sample carries in that cell.
- These are the noise of two halves of the real EPUF, as in other gates. The
  difference is that each half is the size the PSID's own estimate rests on.

**Tolerance**: `tau = K * sigma` with `K = 1`. A gating cell passes if its
gap is finite and `|gap| <= tau`.

**Why K = 1**: suppose a fill's bias in a cell equals one PSID standard
error. Then the root mean square error of a PSID-sized estimate built on
the fill is at most the square root of 2 times the PSID's own sampling
error. A fill within the tolerance is never the larger source of error.

**Operating characteristic**:
- The gap compares the truth and the fill on the same TEST persons, so it
  carries no error from which persons were sampled.
- A fill that draws from the true conditional law has a gap whose standard
  deviation is at most about `sqrt(n / N)` times `sigma`. Here `n` is the
  group's sample size and `N` its pool on a part, roughly 0.09-0.21 on
  DEV-sized parts.
- The floor artifact records this ratio per group (`noise_ratio`). So the
  verdict is close to a step at `|bias| = sigma`. A fill whose bias in a
  cell is near `sigma` can land on either side of it.

**Undefined values**: a gating cell fails if its filled value makes the gap
non-finite.

## 6. Which cells gate, and the checks before lock

A cell gates (`partition`) if, on DEV, all of these hold:
1. its true value is finite, and positive for a log-ratio cell;
2. its floor `sigma` is finite and positive;
3. in at least 95 percent of floor replicates, the smaller sample of the
   pair has at least 20 events. A share's events are the smaller of its
   hits and misses; a correlation's are the pairs in its smallest pair-year.

Every other cell is reported without a verdict. The partition is fixed at
the floor build and recorded in the artifact.

**Bite.** Before lock, on DEV:
- **B1**: the current odd-year rule (`current_odd_fill`) must fail at least
  one gating `odd` cell by more than `2 * tau`.
- **B2**: the current pre-career rule (`current_pre_career_fill`) must fail
  at least one gating `pre` cell by more than `2 * tau`.

If either check fails, the gate does not lock.

**Oracles.** On DEV, two fills that permute true values among similar
persons are scored over `ORACLE_SEEDS = 7200..7219`. They are reported
without a verdict, and no cell is demoted because an oracle fails it.
- **O1** (`odd_oracle_fill`) permutes the true value of each masked odd
  year among DEV persons who share all of: sex; membership of the `odd`
  universe; five-year age band at `t`; and the bins of `t-1` and `t+1`. The
  bins are zero, 20 quantile bins of a positive share of the wage base, and
  at the wage base.
- **O2** (`pre_career_oracle_fill`) permutes whole masked blocks among DEV
  persons who share all of: sex; birth year; membership of the `pre`
  universe; the number of positive years among the first five recorded
  years; and the quintile of their mean share over those years.

The oracles show what a fill with no model error, given only that
conditioning set, would score.

## 7. Candidates

Each family has a primary candidate and a registered alternative.
- All four are fitted on TRAIN only and developed against DEV.
- Each is registered with its code commit and the SHA-256 of its fitted
  artifact before TEST is read.
- Every candidate produces capped earnings. Its draws come from a seeded
  stream per person, keyed by the person id and the draw seed, so a
  person's draw does not depend on which other persons are filled.

### 7.1 Odd years

**Primary: a two-part conditional draw (QRF-style).** It models capped
earnings at `t` as a share of that year's wage base.
- **Conditioning**: the shares at `t-1` and `t+1`, at `t-3` and `t+3` where
  the PSID records them, sex, and age at `t`.
- **Part one**: the probability of a zero year.
- **Part two**: the conditional quantiles of a positive share, including
  the mass at the wage base.
- **Draws**: a uniform per masked year turns into a share through the
  conditional quantile function. A person-level Gaussian copula, learned on
  TRAIN, correlates a person's uniforms across masked years.
- **Training data**: TRAIN years where every conditioning year is recorded.

**Alternative: kNN triples.** It draws the share at `t` from one of the `k`
nearest TRAIN person-years in the shares at `t-1` and `t+1`, sex and age.

### 7.2 Pre-career years

**Primary: rank-kNN donor careers.**
- **Donor pool**: TRAIN persons of the same sex and birth year who are in
  the `pre` universe.
- **Match vector**: a person's percentile rank within the donor pool in
  each of their first five recorded years from their career start.
- **Draw**: one of the `k` nearest donors is chosen by the seeded stream,
  and the whole masked block is copied from that donor. The block covers
  the same calendar years and ages, so it carries the same wage bases.
- **Precedent**: gate 1's passing candidate was rank-kNN
  (`runs/gate1_rank_knn_v5.json`: 10-year autocorrelation 0.499-0.533
  against a reference of 0.539).

**Alternative: a chained one-sided fill.** It draws year `y` from year
`y+1`, sex and age, working backward from the career start to 1951.
- Gate 1's chained weighted QRF baseline failed long persistence
  (`runs/gate1_qrf_baseline_v1.json`: 10-year autocorrelation 0.309-0.368
  against 0.539, tolerance 0.07).
- This alternative is registered so that the choice of borrowing whole
  careers is tested rather than assumed.

### 7.3 Adoption rule

This rule is fixed now, before any candidate exists (`adoption_tier`,
`adopt`). Each candidate and the current rule are scored on the same TEST
persons. A candidate's tier is:
- **certified** if it passes the gate;
- **improves** if it fails the gate but meets both of these:
  - in every gating cell its gap is finite and no larger than the larger of
    the current rule's gap and the tolerance;
  - it fails strictly fewer gating cells than the current rule;
- **not adopted** otherwise.

In each family, the candidate in the better tier is adopted, and the
primary is adopted on a tie. If both are not adopted, the current rule
stays. The two families are adopted separately.

An adopted candidate in the **improves** tier is recorded as an uncertified
improvement, and no text may call it certified.

## 8. Implementation behind the rule

- `estimates/career.py` stays byte-identical. The first-estimates
  birth-evidence reducer seals every file under `src/` against its reviewed
  commit (`scripts/first_estimates_birth_evidence.py`,
  `_assert_input_identity`), and `career.py` is reachable from it.
- The adopted fills live in a new opt-in module. That module is listed in
  the reducer's `POST_REVIEW_SOURCE_EXCLUSIONS`, and a test proves it is
  unreachable from the reducer.
- Its provenance values add `gap_epuf_drawn` and `pre_career_epuf_donor` to
  `career.CareerProvenance`'s values, so a year's provenance always names
  the rule that produced it.
- `cohorts/psid2010.py`, which is outside the seal, gains a spec field for
  the fill. Its default stays the current rule until a new registration of
  the DYNASIM projections adopts the learned fills (section 10).

## 9. Evidence before the floor build

**TRAIN exploration** of the current rules and of conditional-permutation
oracles. Nothing here fitted a candidate, built a DEV floor or read a TEST
person.

The current odd-year rule:
- raises `r1` by 0.047-0.103 and `r2` by 0.068-0.157 across the eight
  strata;
- removes every zero year where a career starts or stops (`zexit`: true
  0.39-0.52, filled 0);
- removes every zero year between two working years (`zint`: true
  0.016-0.037, filled 0);
- moves the median AIME of the 1936-1945 cohorts by 0.2 percent or less.

The conditional-permutation oracles:
- One conditioning on `t-1` and `t+1` only understates `r2` by 0.006-0.032.
- Adding `t-3` and `t+3` cuts that to 0.001-0.015.
- That is why the primary conditions on `t-3` and `t+3` and correlates a
  person's draws.

The current pre-career rule lowers median AIME by:

| Cohort | Men | Women |
|---|---:|---:|
| 1930-1934 | 38% | 40% |
| 1935-1939 | 22% | 28% |
| 1940-1945 | 8% | 14% |

Zeroing only the years before age 22 lowers median AIME by 2-3 percent for
men and 7-11 percent for women born 1930-1945. The PSID-2010 cohort's members
born 1946 or later lose those years under the current rule. That is why
family `pre` covers every year before `max(1968, birth_year + 22)`, not only
1951-1967.

**TRAIN dry run of the floor builder** (10 replicates, 2 oracle seeds,
`--part train`; not a registered floor):
- 131 of 136 cells gate.
- B1 fails 49 of 71 gating odd cells by more than `2 * tau`.
- B2 fails 55 of 60 gating pre cells by more than `2 * tau`.
- An oracle conditioning on `t-1` and `t+1` only failed 13 `r2` and `r4`
  cells by up to 0.04 against tolerances of 0.003-0.03.
- That dry run changed two rules before any DEV floor existed:
  1. **Oracle strata include universe membership.** Without it, O1 mixed in
     persons with no recorded earnings, whose zero years pulled `wint` down
     by about 0.8 in log terms.
  2. **The improves tier was added to the adoption rule.** With a tolerance
     of one PSID standard error, a fill that is far better than the current
     rule can still fail a correlation cell. Without that tier, the current
     rule would stay even when a candidate beats it in every cell.
- Neither change moves a floor, a tolerance or the partition.

## 10. What changes downstream

- The DYNASIM projection comparisons (registered one-shot benchmarks) build
  their cohort with `cohorts.psid2010`, so their AIMEs inherit the fill.
  Adopting a learned fill for them needs a new registration and a new run,
  not a silent rerun. That decision is queued for Max.
- The first-estimates path (`build_career_inclusion`) is sealed historical
  evidence and keeps the current rule.

## 11. Considered and rejected

1. **Floors from two halves of all DEV persons.** Each half would have
   about 440,000 persons, and its sampling error would be a twentieth or
   less of the PSID's. The gate would then demand that a fitted model's bias
   fall below noise that no PSID-based estimate can perceive.
2. **The house tolerance `round(mean |e| + 4 sd |e|, 3)` (about 4.5 sigma).**
   It was built to accept a faithful generator despite sampling noise on
   both sides of a comparison. Here the gap compares the same persons, so
   that noise is absent and the multiple would only loosen the gate.
3. **Scoring the fill by its AIME alone.** On EPUF the current odd-year
   rule moves median AIME by 0.2 percent or less while distorting
   persistence and zero years badly. An AIME-only gate would pass it.
4. **Masking only 1951-1967.** It would leave untested the age-22 part of
   the rule, which lowers AIME for every PSID-2010 member born after 1945.
5. **Weighting the PSID counts.** Effective sample sizes would loosen the
   floors. The unweighted count is the stricter choice.

## 12. Ceremony checklist

- [ ] Rules (this document, the code and tests) pushed before any DEV floor
- [ ] PSID scale counts, `runs/epuf_fill_gate_psid_scale_v1.json`
- [ ] Floor build on DEV, `runs/epuf_fill_gate_floors_v1.json`: floors,
  partition, bite (B1, B2) and oracles (O1, O2)
- [ ] Adversarial referee round (independent Opus 5.5 lane)
- [ ] Fixes; verification round
- [ ] Ratifying merge; lock flip in `gates.yaml`
- [ ] Candidates registered (code commit, fitted-artifact SHA-256)
- [ ] TEST scored once; result published whether it passes or fails
