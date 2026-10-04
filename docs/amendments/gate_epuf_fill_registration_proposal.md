# gate_epuf_fill registration: career fills scored on held-out EPUF careers

- **Registration id**: `2026-10-03-epuf-career-fill`
- **Gate**: `gate_epuf_fill` (registered, `locked: false`; not in
  `gates.yaml` until the lock ceremony in section 11 completes)
- **Surface**: the two rules the career assembler
  (`populace_dynamics.estimates.career.build_career`) uses to fill years the
  PSID did not record, and their learned replacements, scored on held-out
  persons of SSA's 2006 Earnings Public-Use File (EPUF).
- **Ceremony stage**: DRAFT. Rules only. No floor has been built, no
  candidate has been fitted, and no TEST person has been read.
- **Code**: `src/populace_dynamics/harness/epuf_fill_gate.py` (split, masks,
  current rules, cells, floor algebra) and
  `tests/harness/test_epuf_fill_gate.py`.

## What this gate is, in plain words

A gate here is a pass-or-fail test whose rules and thresholds are fixed and
published before anything is scored against it.

The PSID did not ask about income in the odd years 1997 through 2011, and it
began in 1968. The career assembler fills those holes with two fixed rules:

1. each odd year is the mean of the two years around it; and
2. nothing counts before 1968, or before age 22, whichever is later.

EPUF records capped taxable earnings in every year from 1951 to 2006 for a
1 percent sample of Social Security numbers. That lets us hide the years the
PSID would be missing, fill them, and compare the filled careers with the
real ones. This gate does that on persons no fill has seen. A fill passes a
cell if it moves that cell by less than the sampling error the PSID itself
carries there. A fill passes the gate if it passes every cell that gates.

Max approved the direction on 2026-10-03: "at a minimum seems like we could
use it to improve the odd-year filling, we're overstating that form of
persistence with our current method".

## 1. Data

- **Source**: EPUF 2006 (`populace_dynamics.data.epuf`, SHA-256-pinned; PR
  #509). 4,384,254 persons; capped taxable earnings 1951-2006 after SSA's
  disclosure operator; sex and year of birth; no family links, deaths or
  migration. Capped earnings are the AIME's concept.
- **Persons**: sex coded 1 or 2 (3,054 persons with unspecified sex are
  dropped).
- **Wage bases**: EPUF's own (`epuf_operator.wage_base`). **NAWI**:
  `cola_track_a.statutory.captured_ssa_parameters().nawi`.

## 2. Split

Each person's position `u` in [0, 1) is the first eight bytes of
SHA-256(`populace_dynamics.epuf_fill.split.v1|` + decimal person id),
big-endian, over 2^64 (`epuf_fill_gate.split_part`).

| Part | Rule | Persons | Use |
|---|---|---:|---|
| TRAIN | u < 0.6 | 2,629,944 | Fills learn from it; exploration of the current rules |
| DEV | 0.6 <= u < 0.8 | 875,829 | Floors, the bite check, the oracle check; candidate development |
| TEST | u >= 0.8 | 878,481 | Scored once per registered candidate, after lock |

The split was fixed before any EPUF statistic was computed in this work. The
counts include persons of unspecified sex.

## 3. Masks

Two families, masked separately, as the PSID would leave a career:

- **`odd`**: the odd years 1997, 1999, 2001, 2003 and 2005. The assembler
  also fills 2007-2011 and the 2013 seam, which lie past EPUF's last year.
- **`pre`**: every year from 1951 before `max(1968, birth_year + 22)`. For
  cohorts born 1930-1945 that is 1951-1967. For cohorts born 1946-1980 it is
  every year before age 22; EPUF has no earnings below age 15 for cohorts
  born after 1937.

A fill sees every unmasked year of the person, their sex and their year of
birth, and nothing else.

## 4. Cells

Every cell is computed by one function (`odd_cells`, `pre_career_cells`) on
the true matrix and on the filled matrix of the same persons. No universe
reads a masked year, so the true and filled matrices share each cell's
universe and denominators of recorded neighbours.

### 4.1 Family `odd` (64 + 12 cells)

Universe: persons with positive earnings in at least one of the recorded
years 1996, 1998, 2000, 2002, 2004 and 2006. Units are person-years at a
masked year `t`, stratified by sex and age at `t` (18-29, 30-44, 45-59,
60-74).

| Statistic | Definition | Scale |
|---|---|---|
| `r1` | Spearman of `t` against `t-1` and against `t+1`, among units positive in both years; mean of the ten | gap |
| `r2` | Spearman of `t` against `t+2`, both masked, positive in both; mean of four | gap |
| `r4` | Spearman of `t` against `t+4`, both masked, positive in both; mean of three | gap |
| `zint` | Share zero at `t` among units positive at `t-1` and `t+1` | log ratio |
| `zexit` | Share zero at `t` among units positive at exactly one of `t-1`, `t+1` | log ratio |
| `wint` | Share positive at `t` among units zero at `t-1` and `t+1` | log ratio |
| `atcap` | Share at the wage base among units positive at `t` | log ratio |
| `level` | Mean of earnings over the wage base at `t`, zeros included | log ratio |

Career cells: men and women born 1936-1940 and 1941-1945, universe positive
in at least one unmasked year 1968-2006. `aime_p25`, `aime_p50` and
`aime_p75`, the quartiles of the AIME under the 35-year rule through age 61
(`epuf_fill_gate.aime_35`; a Hypothesis test pins it to
`ss.statutory_aime.aime`).

### 4.2 Family `pre` (18 + 24 + 18 cells)

Universe: persons with positive earnings in at least one year from
`max(1968, birth_year + 22)` through 2006.

- Men and women born 1930-1934, 1935-1939 and 1940-1945 (masked years
  1951-1967): `aime_p25`, `aime_p50`, `aime_p75`; `pzero`, the share of masked
  person-years at ages 18 and over with no earnings; `plevel`, their mean
  earnings over the wage base; `pr_in`, the Spearman of 1962 against 1967
  (both masked); `pr_cross`, the Spearman of 1965 against 1970 (masked
  against recorded). Correlations among persons positive in both years.
- Men and women born 1946-1955, 1956-1965 and 1966-1980 (masked years: ages
  21 and under): `yzero` and `ylevel` over ages 15-21, and `yr_cross`, the
  Spearman of earnings at age 21 against age 24.

## 5. Gap, floor and tolerance

- **Gap.** For a correlation, filled minus true. For every other cell, the
  log of filled over true (`epuf_fill_gate.gap`). A candidate's gap is the
  mean over 20 draw seeds (`DRAW_SEEDS = 7100..7119`; no gate or floor seed
  reuses them).
- **Floor.** The cell's sampling standard error at the PSID's size: the root
  mean square of `[m(A) - m(B)] / sqrt(2)` over 200 replicate pairs of
  disjoint samples of real DEV persons eligible for the cell
  (`epuf_fill_gate.floor_sigma`; replicate seeds `[5000 + cell index, 200,
  n]`). The sample size `n` is the PSID's:
  - for `odd` cells, the number of PSID-2010 cohort person-years the
    assembler fills in that sex and age band, divided by the mean number of
    masked person-years per eligible DEV person in the band;
  - for career and `pre` cells, the number of PSID-2010 cohort members in
    that sex and cohort.

  Counts come from the default-spec PSID-2010 cohort
  (`cohorts.psid2010.build_psid2010_cohort`), unweighted. The PSID is
  weighted, and its effective sample size is smaller than its count, so a
  floor on the count is narrower, and the gate stricter, than the PSID's real
  sampling error. The counts are stored in the floor artifact with the PSID
  files' SHA-256 from the cohort's provenance.
- **Tolerance.** `tau = K * sigma` with `K = 1`. A fill passes a cell if
  `|gap| <= tau`.
- **Why K = 1.** A fill whose bias in a cell is one PSID standard error
  raises that cell's root mean square error at the PSID's size by a factor
  of at most the square root of 2. Below that, the fill's error is smaller
  than the error the PSID sample already carries. Above it, the fill would
  be the larger source of error.
- **Operating characteristic.** The gap is measured on the same TEST persons
  for the truth and the fill, so it carries no sampling noise from who was
  sampled. Only the fill's own draws (averaged over 20 seeds) and the TEST
  sample's size enter. TEST is about 900 times the PSID's cell sizes, so the
  verdict is close to a step at `|bias| = sigma`. The floor build records,
  for every cell, the spread of the gap over the 20 seeds of each oracle and
  bite rule (section 6), so the size of that noise next to `tau` is on file
  before lock.
- **Undefined values.** A cell whose true value is finite and whose filled
  value is not finite, or whose log ratio is infinite, fails. A cell whose
  true value is undefined is not eligible.

## 6. Which cells gate, and the checks before lock

A cell gates if, on DEV:

1. its true value is finite and, for a log-ratio cell, positive;
2. the events behind it (the smaller of a share's hits and misses; a
   correlation's pairs in its smallest pair) number at least 20 in the
   PSID-size sample, taking the smaller of each replicate pair, in at least
   95 percent of replicates; and
3. its floor `sigma` is finite and positive.

Every other cell is reported without a verdict. The partition is fixed at the
floor build and recorded in the artifact.

**Bite.** Before lock, on DEV:

- **B1**, the current odd-year rule (`current_odd_fill`), must fail at least
  one gating `odd` cell by more than `2 * tau`;
- **B2**, the current pre-career rule (`current_pre_career_fill`), must fail
  at least one gating `pre` cell by more than `2 * tau`.

TRAIN exploration already shows both by wide margins (section 9). If either
check failed on DEV, the gate would not lock.

**Oracles.** On DEV, two fills that draw from the empirical conditional
distribution of the scored data itself are scored and reported:

- **O1** permutes the true value of each masked odd year among DEV units
  sharing sex, age band, year, and the bins of `t-1` and `t+1` (zero; 20
  quantile bins of positive share of the wage base; at the wage base);
- **O2** permutes whole masked pre-career blocks among DEV persons sharing
  sex, birth year and the bins of their first five recorded years.

They show what a fill with no model error, given only that conditioning set,
would score. They are reported, and no cell is demoted because an oracle
fails it.

## 7. Candidates

Each family has a primary candidate and a registered alternative. All four
are fitted on TRAIN only and developed against DEV. Each is registered,
with its code commit and the SHA-256 of its fitted artifact, before TEST is
read.

### 7.1 Odd years

- **Primary: a two-part conditional draw (QRF-style).** It models capped
  earnings at `t` as a share of that year's wage base.
  - The conditioning set is the shares at `t-1` and `t+1`, at `t-3` and `t+3`
    where the PSID records them, sex, and age at `t`.
  - Part one is the probability of a zero year. Part two is the conditional
    quantiles of a positive share, including the mass at the wage base.
  - The draw takes a uniform from a seeded per-person stream. A person-level
    Gaussian copula correlates a person's uniforms across masked years, with
    the correlation learned on TRAIN.
  - It is fitted on TRAIN years where every conditioning year is recorded.
  - The result is a share of the wage base, so the filled year is capped
    taxable earnings, the AIME's concept.
- **Alternative: kNN triples.** It draws the share at `t` from one of the
  `k` nearest TRAIN person-years in the shares at `t-1` and `t+1`, sex and
  age.

### 7.2 Pre-career years

- **Primary: rank-kNN donor careers.**
  - The donor pool is TRAIN persons of the same sex and birth year with
    positive earnings in at least one year from their career start through
    2006.
  - A person's match vector is their percentile rank, within the donor pool,
    in their first five recorded years from their career start.
  - Among the `k` nearest donors, one is chosen by the seeded stream. The
    whole masked block is copied from that donor: the same calendar years
    and ages, so the same wage bases.
  - Gate 1's passing candidate was rank-kNN (`runs/gate1_rank_knn_v5.json`,
    10-year autocorrelation 0.499-0.533 against a reference of 0.539).
- **Alternative: a chained one-sided fill.** It draws year `y` from year
  `y+1`, sex and age, backward from the career start to 1951.
  - Gate 1's chained weighted QRF baseline failed long persistence
    (`runs/gate1_qrf_baseline_v1.json`: 10-year autocorrelation 0.309-0.368
    against 0.539, tolerance 0.07). This alternative is registered so that
    the choice of borrowing whole careers is tested rather than assumed.

### 7.3 Adoption rule

Fixed now, before any candidate exists:

- In each family, the primary is adopted if it passes.
- If the primary fails and the alternative passes, the alternative is adopted
  and the record says so.
- If both fail, nothing is adopted and the current rule stays.

The two families are adopted separately.

## 8. Implementation behind the rule

- `estimates/career.py` stays byte-identical. The first-estimates
  birth-evidence reducer seals every file under `src/` against its reviewed
  commit (`scripts/first_estimates_birth_evidence.py`,
  `_assert_input_identity`), and `career.py` is reachable from it.
- The adopted fills live in a new opt-in module. It is listed in the
  reducer's `POST_REVIEW_SOURCE_EXCLUSIONS` and proven unreachable from the
  reducer. Its provenance values extend `career.CareerProvenance` with
  `gap_epuf_drawn` and `pre_career_epuf_donor`, so a year's provenance always
  names the rule that produced it.
- `cohorts/psid2010.py`, which is outside the seal, gains a spec field for
  the fill. Its default stays the current rule until a new registration of
  the DYNASIM projections adopts the learned fills (section 10).

## 9. Exploration before registration (TRAIN only)

Computed on TRAIN with the current rules and with conditional-permutation
oracles; no candidate fitted, no DEV floor, no TEST person read.

- The current odd-year rule:
  - raises `r1` by 0.047-0.103 and `r2` by 0.068-0.157 across the eight
    strata;
  - leaves no zero year in a year where a career starts or stops (`zexit`
    true 0.39-0.52, filled 0), and none between two working years (`zint`
    true 0.016-0.037, filled 0);
  - moves median AIME of the 1936-1945 cohorts by 0.2 percent or less.
- An oracle conditioning on `t-1` and `t+1` only understates `r2` by
  0.006-0.032. Adding `t-3` and `t+3` cuts that to 0.001-0.015. That is why
  the primary conditions on them and correlates a person's draws.
- The current pre-career rule lowers median AIME by 38, 22 and 8 percent
  for men born 1930-1934, 1935-1939 and 1940-1945, and by 40, 28 and 14
  percent for women.
- Zeroing only the years before age 22 lowers median AIME by 2-3 percent
  for men and 7-11 percent for women born 1930-1945. The PSID-2010 cohort's
  members born 1946 or later lose those years under the current rule. That
  is why family `pre` covers every year before `max(1968, birth_year + 22)`,
  not only 1951-1967.

## 10. What changes downstream

- The DYNASIM projection comparisons build their cohort with
  `cohorts.psid2010`, so their AIMEs inherit the fill. They are registered
  one-shots. Adopting a learned fill for them needs a new registration and a
  new run, not a silent rerun. That decision is queued for Max.
- The first-estimates path (`build_career_inclusion`) is sealed historical
  evidence and keeps the current rule.

## 11. Ceremony checklist

- [ ] Rules (this document, the code and tests) pushed before any DEV floor
- [ ] Floor build on DEV: floors, partition, bite (B1, B2) and oracles (O1,
  O2); artifact `runs/epuf_fill_gate_floors_v1.json`
- [ ] Adversarial referee round (independent Opus 5.5 lane)
- [ ] Fixes; verification round
- [ ] Ratifying merge; lock flip in `gates.yaml`
- [ ] Candidates registered (code commit, fitted-artifact SHA-256)
- [ ] TEST scored once; result published whether it passes or fails
