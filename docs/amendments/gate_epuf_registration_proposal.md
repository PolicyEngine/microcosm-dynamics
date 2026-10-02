# gate_epuf registration: generated earnings histories against SSA's Earnings Public-Use File

- **Registration id**: `2026-10-02-epuf-covered-earnings`
- **Gate**: `gate_epuf` (registered, unlocked; not in `gates.yaml`)
- **Surface**: tranche G, the gate-1 generator's earnings on the four even
  reference years 1998-2004, by sex and birth cohort, scored against SSA's 2006
  Earnings Public-Use File (EPUF). Tranche R, the career statistics, is
  report-only.
- **Ceremony stage**: CLOSED WITHOUT LOCK after referee round 1
  (`reviews/gate_epuf_round1_referee_20261002.md`), verified in round 2
  (`reviews/gate_epuf_round2_verification_20261002.md`). **The gate gates
  nothing.** A run reports every cell without a pass or fail. This
  registration edits no `gates.yaml` cell and no committed `runs/*.json`; its
  record is `docs/design/gate_epuf_block_draft.yaml` (`locked: false`,
  `status: unlocked_report_only`).
- **Class**: new gate, unlocked. No model has been scored against it.
- **Evidence base**: `runs/epuf_gate_floors_v1.json` (floors, bridges,
  partition, operating characteristic, bite demonstrations);
  `runs/epuf_gate_floors_v1_first_build.json` (the first build, frozen);
  `runs/epuf_gate_supplement_v1.json` (bite shifts and power, birth-year mix);
  `data/external/epuf_2006/` (provenance, SSA's documentation, published
  tables, disclosure constants); `runs/gate1_rank_knn_v5.json` (the gate-1 run
  whose generator this gate would score).

## Outcome, in plain words

A gate here is a pass-or-fail test whose rules and thresholds are fixed and
published before the model is scored against it.

This registration set out to make SSA's public earnings file such a test for
the model's generated earnings. **As registered, it has not been shown to
catch anything gate 1 does not already catch, and it could not meet its own
check on its bite, so it does not lock.**

- The generator's earnings overlap EPUF in four years, 1998-2004. On that
  overlap only two cells had the power the rules demand: how persistent
  earnings ranks are from 1998 to 2004, for men and for women.
- Those two cells fail a generator whose persistence falls about 0.10 below
  the PSID's four times in five, and one about 0.11 below nine times in ten.
  The interval also ends 0.08 above EPUF, so one that overshoots EPUF by
  more than that fails more often than not. The
  registered check on the gate's own bite asked for more: that it catch a
  smaller shortfall, 0.07 for men and 0.06 for women, nine times in ten. The
  rules could not deliver that. That was a flaw in the registration, not a
  surprise in the data: a check of the dose against the cells' detection
  point before the build would have shown it.
- A perturbation that draws each person's early years from donors of both
  sexes raised men's persistence to about EPUF's level, which the cells
  accept. No perturbation was shown to pass gate 1 and fail these cells.
- With the PSID's distance from EPUF now public, the registered candidate's
  verdict on these cells could largely be predicted.

The independent referee ruled against loosening the check to fit the result,
and this registration takes that ruling (section 7.5). What EPUF does add is
measurement. The figures below are means over the three birth-cohort bands,
on the generator's support. The PSID's earnings ranks persist less than
SSA's records (0.668 against 0.711 for men; in five of the six sex-by-cohort
cells). PSID men are at the taxable maximum more often (17.8 against 11.6
percent of positive person-years). Fewer PSID men have a zero year before
covered work in 2004 (9.7 against 12.8 percent). A run that regenerates a
gate-1 candidate reports these comparisons for every cell, and where the
candidate sits between the PSID and EPUF
(`populace_dynamics.harness.epuf_run.report_candidate`); no run script calls
that path yet. Section 12 says what a gate with real bite would need.

## 1. Summary

Gate 1 scores the model's generated earnings histories against held-out PSID
records. Experts who work with administrative earnings will ask how those
histories compare with SSA's own records. DYNASIM and MINT start from surveys
matched to SSA earnings, and CBOLT from the Continuous Work History Sample; all
three are confidential. EPUF is public: a 1 percent sample of Social Security
numbers issued before 2007, with year of birth, sex and capped taxable earnings
for each year from 1951 to 2006
(<https://www.ssa.gov/policy/docs/microdata/epuf/index.html>).

This registration scores the gate-1 generator against EPUF. Three facts shaped
it.

1. **The generator and EPUF overlap in four years.** The gate-1 generator
   redraws earnings on each held-out person's observed PSID periods, which are
   the even reference years 1998 to 2022 at ages 25 to 59
   (`scripts/run_gate1_candidate10.py:258-298`). EPUF ends in 2006, and its
   2005 and 2006 are short from late posting. The scoreable overlap is 1998,
   2000, 2002 and 2004. Nothing in the repository generates earnings for years
   before 1998. The forward earnings law generates earnings from 2015 on
   (`engine/forward_earnings.py`). The careers that benefit figures rest on
   are observed PSID earnings from 1968, with rule-based fills
   (`src/populace_dynamics/estimates/career.py:964-1076`).
2. **The PSID itself sits at some distance from EPUF.** PSID labor income
   counts noncovered work, the gate-1 panel holds heads and spouses who stay
   in the survey, and earnings are reported, not filed. A generator trained on
   the PSID inherits that distance. A gate that demands agreement with EPUF to
   within sampling noise would fail every PSID-trained generator, and the
   better the generator copied the PSID the more surely it would fail.
3. **A 20-seed mean has noise that its seeds share.** Each seed scores
   generated values against the same realised PSID sample, so averaging over
   seeds removes only part of the noise.

The design that followed: score the mean over the gate's 20 registered seeds;
accept a cell when the generated value lies between EPUF and the PSID's own
position, plus a tolerance set from a real-data floor that includes the shared
noise; and gate a cell only when that whole acceptance band stays inside a
power cap. Cells that could not meet that are published with the reason.

The four career statistics the request named are years without earnings by
age 62, rank persistence ten years apart, the share at the taxable maximum by
age, and the AIME under the 35-year rule. None can be scored on generated
histories, because nothing generates a career's earnings before 1998. They are registered
as tranche R, report-only, with their EPUF reference values in the floor
artifact.

## 2. What is scored

**Candidate.** Any generator that emits gate 1's candidate panel: for a
holdout drawn by `populace_dynamics.harness.panel.split_panel_by_person`
(`fraction=0.2`, seed `s`) from gate 1's filtered panel, the holdout's persons
on their observed periods with generated `earnings`. The first candidate it
would score is the gate-1 passing generator (`runs/gate1_rank_knn_v5.json`,
candidate 11).

**Seeds.** The 20 seeds 0-19, the set gate 1's `c2st_mean_rule` already
registers (`gates.yaml:209-216`). The scored quantity for a cell is the mean
of its 20 per-seed values, then the cell's transform (log for shares, identity
for rank correlations).

**Support.** A person of gate 1's filtered panel (age 25-59, reference years
1998-2022, positive weight) is in the support if all four hold:

1. the person has a row at each of 1998, 2000, 2002 and 2004;
2. the person's last in-filter period is 2006 or later. The generator keeps
   each person's last period at its real value, so this rule keeps real values
   out of the window: every scored value is generated;
3. sex is coded male or female (`ER32000`, read by
   `populace_dynamics.data.deaths.read_death_records`);
4. birth year, `floor(median(period - age) + 0.5)` over the person's rows, lies
   in 1947-1973.

A support person's weight is their 2004-row weight. The support depends only on
the real panel, never on generated values. The EPUF side is every EPUF person
with sex 1 or 2 born 1947-1973, with weight 1; EPUF has no presence condition
to mirror, so each statistic carries its own conditioning (section 3).

The PSID birth year is derived from age at interview, which is measured in
the wave after the income year, so it can sit a year below EPUF's year of
birth. The repository's career products take a marriage-history birth year
first (`estimates/career.py:650-656`); this registration does not. The
supplement stores each band's birth-year mix on both sides
(`runs/epuf_gate_supplement_v1.json`, `birth_year_mix`). Their means agree
within 0.25 years, but that compares the two sides' own labels after each
was selected on its label, so it does not measure the shift.

**Units.** PSID-side and candidate-side earnings pass through EPUF's
measurement operator (`populace_dynamics.harness.epuf_operator.epuf_measure`):
cap at the year's contribution and benefit base, replace positive values below
$100 with the year's EPUF bottom code, replace values within one rounding base
below the cap with the year's EPUF band mean, and round the rest to SSA's base
($25, $100 or $1,000). The operator preserves whether a person-year is
positive and whether it is exactly at the cap. SSA rounded at random and did
not publish the probabilities; the operator rounds half up. EPUF is used as
published.

**Validation only.** No candidate may use EPUF in fitting, tuning or
calibration, and EPUF enters nothing upstream of the model. A candidate that
uses it is scored and labelled a calibration check.

## 3. Cells

Cohort bands: c0 = born 1947-1955, c1 = 1956-1964, c2 = 1965-1973. Every
statistic is computed within sex and cohort band. A sex-level cell is the
unweighted mean of its three band values, which holds cohort composition at
one-third each on both sides.

| Cell | Statistic | Conditioning | Metric and cap |
|---|---|---|---|
| `r6` | Weighted Spearman correlation of 1998 and 2004 earnings (average ranks for ties) | positive in 1998 and in 2004 | absolute gap, 0.15 |
| `zint` | Share with no earnings in 2000 or in 2002 | positive in 1998 and in 2004 | log ratio, ln 1.5 |
| `d_anyzero` | Share with no earnings in at least one of 1998, 2000, 2002 | positive in 2004 | log ratio, ln 1.5 |
| `q_atmax` | Share of positive person-years exactly at the wage base, 1998-2004 | positive person-years | log ratio, ln 1.5 |
| `mpers` | Share at the wage base in 1998 | at the wage base in 2004 | log ratio, ln 1.5 |
| `q_sexratio` | Men's `q_atmax` over women's | as `q_atmax` | log ratio, ln 1.5 |

Each statistic conditions on covered earnings at one or both ends of its span.
EPUF has no date of death and no record of arrival or departure, so an EPUF
year without earnings can be a year after death or before arrival; a person
with earnings at the end of a span was alive and in covered work then.

How these stand to the request's four candidates:

| Requested | Here | Why |
|---|---|---|
| Years with zero capped earnings by age 62 | `zint` and `d_anyzero` (interior and earlier zero years inside the window); the by-62 count is tranche R | the generator emits four window years, not careers |
| Rank persistence ten years apart | `r6`, six years apart | the longest generated span inside EPUF's reliable years is 1998 to 2004 |
| Share at the taxable maximum by age | `q_atmax`, `mpers`, `q_sexratio` by sex and cohort band | adopted; within four calendar years a cohort band is an age band |
| AIME under the 35-year rule | tranche R only | needs a career |

The generator never sees sex. Its inputs are age, period and earnings ranks,
and its levels are quantiles of sex-pooled age-by-period marginals
(`scripts/run_gate1_candidate10.py:557-562`). Gate 1 scores sex-pooled
moments, so cells by sex were meant to test something gate 1 does not. The
bite demonstrations found no such catch (section 7.4).

## 4. Floor, tolerance and acceptance interval

Write `theta_E` for a cell's EPUF value, `theta_P` for its value on the real
PSID support, both on the cell's metric scale, and `B = theta_P - theta_E`
for the bridge.

**Floor.** For replicates `b = 0..99`, on the real PSID support:

    e_b = [m(A_b) - m(B_b)] / 2
          + pooled(m(H_b0), ..., m(H_b19)) - pooled(m(T_b0), ..., m(T_b19))

`A_b`, `B_b` are person-disjoint halves (split seed `b`, fraction 0.5).
`H_bj`, `T_bj` are a 20% holdout and its complement under the gate's split
function (seed `1000 + 20b + j`). `pooled` is the 20-seed estimate of
section 2. The first term stands for the noise the 20 seeds share: a faithful
generator's mean differs from the real value by the realised sample's own
deviation from its conditional law, which is the same on every seed. The
term bounds that noise, and the bound is exact for a generator that draws
from the true law. A generator that copies donors from the same sample, as
candidate 11 does, likely has less of it, in which case the floor is
conservative for it. The second term stands for the noise that averages down: who
falls in each holdout, each seed's draws and each seed's fit.

**Tolerance.** `t = round(mean|e_b| + 4 * sd|e_b|, 3)`, with sd taken with
`ddof=1` and `k = 4` on every cell. The value 4 was fixed without an
operating-characteristic rule. House gates choose k against one (gate_m4) or
use 3 (gate_m6). For a single 20-seed decision, `k = 4` gives a per-cell false
fail rate near 7 in 10,000. `sigma` is the root mean square of `e_b`.

**Acceptance.** With `G` the candidate's estimate less `theta_E`, a cell
passes iff

    min(0, B) - t  <=  G  <=  max(0, B) + t

The bridge is never subtracted. Subtracting it would cancel `theta_E` and
turn the gate into a second gate 1. The interval is one-sided in the bridge:
it reaches from EPUF to the PSID's position and `t` beyond each, so a
candidate that overshoots EPUF on the far side from the PSID fails.

**Faithful-candidate pass probability.** A candidate that reproduces the
PSID has `G = B + noise`. Per cell the probability is
`Phi((upper - B)/sigma) - Phi((lower - B)/sigma)`. The gate's is the product
over gated cells, reported beside the share of floor replicates in which
every gated cell's `B + e_b` lies inside its interval.

## 5. Which cells gate

A cell's reason for not gating is the first of these that applies:

1. `undefined_on_some_split`: the statistic is undefined on some floor split.
2. `below_20_events`: fewer than 20 events on some half, some 20% holdout of
   the 2,000 floor splits, or some real gate-seed holdout. Events are the
   smaller of a share's numerator and its complement, or a correlation's
   pairs. A sex-level cell sums its three bands' events; the house rule is
   per cell, so a future registration should take the weakest band.
3. `epuf_sampling_not_negligible`: EPUF's own sampling sd (50 random groups)
   exceeds 0.1 `sigma`.
4. `noise_exceeds_cap`: `t + 0.8416 sigma` exceeds the cap.
5. `bridge_exceeds_budget`: `|B| + t + 0.8416 sigma` exceeds the cap.

Rules 4 and 5 make the cap bind on the 80 percent power point, not on the
tolerance. A candidate whose distance from EPUF reaches the cap fails with
probability at least 0.8, and passes up to one time in five.

Among eligible cells:

- `r6`: gate all six sex-by-cohort cells if every one is eligible; otherwise
  gate each eligible sex-level cell.
- participation: per sex, gate `zint` if eligible, otherwise `d_anyzero` if
  eligible.
- tail: gate each eligible sex-level `q_atmax` and `mpers` cell and
  `q_sexratio`.
- every other cohort-level cell is reported.

**No gated cell.** If no cell gates, the registration does not lock as a
pass-or-fail gate. It publishes as `report_only_bridge_dominated`, with the
bridge table as its finding.

**Pauses.** The ceremony pauses if the faithful-candidate pass probability of
the gated surface is below 0.90, or if a gated family's bite demonstration
fails less than 90 percent of the time (section 6).

**Pass rule.** The gate passes iff every gated cell passes on the 20-seed
estimate. A verdict attaches to the registered candidate only if the run
reproduces that candidate's committed gate-1 artifact exactly. For seeds
5-19 that artifact stores only one statistic per seed, so a future
registration should commit digests of the generated panels.

## 6. Bite demonstrations

Each is a perturbation of the real PSID support, scored on the 20 gate
holdouts as a candidate would be, over 50 perturbation seeds. No candidate is
generated.

| Bite | Perturbation, as computed | Required of |
|---|---|---|
| `bd1` | With probability 0.10 (and, reported, 0.05) a person takes the 1998-2002 earnings of a donor drawn with replacement from the same sex and band, who can be the person themself | persistence, if gated |
| `bd2` | Everyone takes the 1998-2002 path of a donor in the same band and 2004 class (no earnings, or decile of 2004 earnings), drawn from both sexes | reported |
| `bd2c` | As `bd2`, donors of the person's own sex: the control that isolates pooling the sexes | reported |
| `bd3` | In each of 1998-2002, values whose rank among the year's positive values (ties at their highest rank, sexes and bands pooled) exceeds 0.92 move, with probability 0.5, to the value at a rank drawn uniformly from 0.5 to 0.92; every value at the cap is eligible to move | tail, if gated |
| `bd4` | Each positive 1998-2002 person-year becomes zero with probability 0.03 | participation, if gated |

The real gate-seed holdouts are also scored as a training copy and must pass.

These fail shares perturb the realised sample and score it on the fixed gate
holdouts. They therefore leave out the noise the seeds share, which a
generator's verdict includes. `runs/epuf_gate_supplement_v1.json` adds each
bite's mean shift and its power under the gate's own noise model.

## 7. Results of the floor build

The numbers in this section come from `runs/epuf_gate_floors_v1.json` and
`runs/epuf_gate_supplement_v1.json`. `tests/test_gate_epuf_block_draft.py`
recomputes every tolerance, interval, partition, pass probability, detection
point, bite shift and power figure from what those files store. Each
sex-level figure is the unweighted mean of its three birth-cohort bands.

### 7.1 Support

| | Persons |
|---|---:|
| gate 1's filtered panel | 22,300 |
| with a row at each of 1998, 2000, 2002, 2004 | 6,323 |
| and last in-filter period 2006 or later | 5,775 |
| and coded sex | 5,775 |
| and born 1947-1973 (the support) | 5,769 |

By sex and cohort band: men 898 / 926 / 679 and women 1,059 / 1,269 / 938
(c0 / c1 / c2). EPUF's side is 1,311,282 persons. The builder asserted that
its split function draws gate 1's holdouts: each gate seed's holdout size
equals `runs/gate1_rank_knn_v5.json`'s for seeds 0-4.

### 7.2 The PSID against EPUF

Sex-level cells. "Bridge" is the PSID's distance from EPUF on the cell's
metric scale (log ratio for shares, difference for correlations).

| Cell | EPUF | PSID | Bridge | Tolerance `t` | Outcome under the registered rules |
|---|---:|---:|---:|---:|---|
| `r6.men` | 0.711 | 0.668 | -0.043 | 0.079 | selected |
| `r6.women` | 0.672 | 0.640 | -0.032 | 0.078 | selected |
| `zint.men` | 0.051 | 0.049 | -0.040 | 0.381 | below 20 events |
| `zint.women` | 0.066 | 0.070 | +0.062 | 0.381 | below 20 events |
| `d_anyzero.men` | 0.128 | 0.097 | -0.278 | 0.283 | bridge exceeds budget |
| `d_anyzero.women` | 0.180 | 0.151 | -0.176 | 0.212 | bridge exceeds budget |
| `q_atmax.men` | 0.116 | 0.178 | +0.424 | 0.164 | bridge exceeds budget |
| `q_atmax.women` | 0.036 | 0.039 | +0.086 | 0.358 | noise exceeds cap |
| `mpers.men` | 0.594 | 0.613 | +0.031 | 0.196 | below 20 events |
| `mpers.women` | 0.478 | 0.516 | +0.077 | — | undefined on some split |
| `q_sexratio` | 3.25 | 4.56 | +0.338 | 0.379 | noise exceeds cap |

What the table says, and what it does not:

- **Rank persistence.** On the support, PSID earnings ranks persist less
  from 1998 to 2004 than EPUF's do: 0.668 against 0.711 for men, 0.640
  against 0.672 for women. That holds in five of the six sex-by-cohort
  cells; for women born 1956-1964 the PSID's is 0.017 higher. The bridge
  measures the gap. It does not say how
  much of it comes from reporting, from who the PSID samples, or from
  noncovered work.
- **The taxable maximum.** Among positive person-years, 17.8 percent of the
  PSID support's men are at the wage base, against 11.6 percent of EPUF's
  men born in the same years. The support is people who stayed in the survey
  as heads or spouses through 2006, and EPUF is every Social Security number;
  the artifact does not separate how much of the gap that difference
  explains. A log gap of 0.42 exceeds the cap, so the cell is reported.
- **Zero years.** Given covered earnings in 2004, fewer PSID men and women
  had a zero year in 1998-2002 than EPUF's (9.7 against 12.8 percent for
  men). EPUF records only covered earnings, so a year of noncovered work is a
  zero there and not in the PSID; how much of the gap that accounts for is
  not measured here.
- **Power.** Interior zero years and persistence at the maximum are too rare
  at the PSID's size for the 20-event rule. One cohort-band cell is eligible
  (`r6.women.c1`); the ladder gates cohort cells only when all six are, so it
  is reported.

### 7.3 The cells the rules selected, and their operating characteristic

The ladder fell back to sex-level persistence and selected two cells:

| Cell | Interval for `G` | Realised sigma | Shared-noise share of floor variance | Faithful pass probability |
|---|---|---:|---:|---:|
| `r6.men` | [-0.122, 0.079] | 0.0246 | 0.78 | 0.9993 |
| `r6.women` | [-0.111, 0.078] | 0.0248 | 0.73 | 0.9993 |

The faithful-candidate pass probability of the two is 0.9986 by product, and
in 100 of 100 floor replicates both cells' `B + e_b` lie inside their
intervals. The real gate-seed holdouts, scored as a candidate, pass (`G` =
-0.044 for men and -0.045 for women). About three-quarters of each cell's
floor variance is the term the 20 seeds share, which a floor of 20%/80%
splits alone would have left out.

### 7.4 Bite demonstrations, and why the pause was built in

| Bite | Fails the gate (fixed holdouts) | Mean shift, men / women | Power under the gate's noise model, men / women |
|---|---:|---|---|
| `bd1`, 10% of persons | 0.44 | -0.067 / -0.057 | 0.30 / 0.19 |
| `bd1`, 5% of persons | 0.00 | -0.033 / -0.030 | 0.03 / 0.02 |
| `bd2`, donors from both sexes | 0.00 | +0.056 / -0.006 | 0.00 / 0.00 |
| `bd2c`, same-sex donors (control) | 0.00 | +0.007 / +0.010 | 0.00 / 0.00 |
| `bd3`, top-tail compression | 0.42 | -0.076 / -0.005 | 0.45 / 0.00 |
| `bd4`, participation loss | 0.00 | +0.001 / -0.001 | 0.00 / 0.00 |

The registered requirement for the persistence family is that `bd1` at 10
percent fails at least 90 percent of the time. It fails 44 percent of the
time on the fixed holdouts, so **the ceremony paused** (section 5).

The requirement could not have been met. Under the gate's own noise model the
two cells fail a shortfall from the PSID of 0.100 (men) and 0.100 (women)
four times in five, and of 0.111 and 0.110 nine times in ten
(`detection_points` in the supplement). `bd1` at 10 percent shifts the
correlation by 0.067 for men and 0.057 for women, inside both points. The
eligibility rule promised 80 percent power at the first point; the bite asked
for 90 percent at a smaller shortfall. The registration never checked the
dose against the cells' detection point. Doing so on EPUF subsampled to PSID
scale, before the build, would have shown the requirement was out of reach.
So the pause comes from an internal inconsistency of the registration, not
from something the data revealed.

Two more readings, both from the supplement:

- Donors drawn from both sexes (`bd2`) raise men's persistence by 0.056, to
  about EPUF's level and 0.012 past it, where the interval accepts it. `bd2`
  is a perturbation of real data, not a generator. Its donors are matched on
  2004 deciles, and the same-sex control (`bd2c`) moves the cells by 0.01 or
  less, so the matching itself keeps the rank correlation. Within that limit,
  the cells by sex showed no catch for pooling the sexes.
- No perturbation was shown to pass gate 1's battery and fail these cells.
  Their catch beyond gate 1 is not demonstrated.

### 7.5 Referee round 1 and the ruling

Three options were put to the referee round: (a) lock the two persistence
cells and restate the bite requirement at what they demonstrably detect;
(b) redesign the surface for power; (c) publish the comparison report-only.

The referee (`reviews/gate_epuf_round1_referee_20261002.md`, verdict AMEND)
rejected (a). A requirement rewritten to match a gate's demonstrated power no
longer tests anything. Locking now, with the bridges' signs known, would
choose a gate the registered candidate very likely passes. Candidate 11
persists more than the PSID at two and four years in gate 1, which here moves
it toward EPUF, inside the interval. The referee also ruled that (b) cannot be
done blind, because every redesign it names is informed by the bridges.

**Ruling: the gate does not lock.** A run reports every cell without a pass
or fail: the candidate's 20-seed estimate, its distance from EPUF, and that
distance split into the candidate's distance from the PSID and the PSID's
distance from EPUF (`populace_dynamics.harness.epuf_run.report_candidate`).
No run script calls that path yet; a run that regenerates a gate-1
candidate's 20 panels hands them to it. The drafting session had recommended
(a); it withdraws that recommendation. A gate with bite needs a fresh
registration (section 12).

Round 2 (`reviews/gate_epuf_round2_verification_20261002.md`) verified this
record and asked for the fixes now applied: a reporting path that covers
every cell and returns no pass or fail, and corrected wording.

### 7.6 Tranche R on EPUF alone

These numbers use no PSID. They compare EPUF careers as published with the
same careers rewritten by two of the career assembler's rules (section 8).

| Cohort | Mean zero years, ages 22-61 | Median AIME | 25th percentile AIME |
|---|---|---|---|
| men 1930-1934 | 13.9 -> 23.7 | $1,551 -> $1,000 | $429 -> $135 |
| men 1935-1939 | 13.0 -> 19.7 | $1,999 -> $1,548 | $611 -> $316 |
| men 1940-1944 | 12.9 -> 15.7 | $2,491 -> $2,240 | $758 -> $560 |
| women 1930-1934 | 23.2 -> 28.3 | $344 -> $182 | $57 -> $1 |
| women 1935-1939 | 21.5 -> 24.9 | $528 -> $367 | $110 -> $26 |
| women 1940-1944 | 19.2 -> 20.9 | $835 -> $698 | $202 -> $114 |

The two rules alone lower the median AIME of men born 1940-1944 by 10 percent,
and of those born 1930-1934 by 36 percent, because they count earnings before
1968 as zero. A cohort born in 1946 or later loses no year to that rule, so
the table shows the size of the effect where it applies, not across the
repository's benefit cohorts.

## 8. Tranche R: career statistics, report-only

Report-only and never gated. The statistics are the request's four, on annual
capped histories at ages 22-61, by sex and birth cohort (1930-1934,
1935-1939, 1940-1944: the cohorts whose whole window lies inside 1951-2006):

- years without earnings (mean, quartiles, share with ten or more, share with
  all 40);
- Spearman correlations 1980 to 1990 and 1994 to 2004, among those positive in
  both years;
- share of positive person-years at the wage base, by age band;
- AIME under the 35-year rule, ranking every year after 1950 through age 61
  (quartiles, 90th percentile, share zero), matching
  `populace_dynamics.ss.statutory_aime.aime`.

The floor artifact holds their EPUF values twice: on EPUF as published, and
on EPUF rewritten by two of the career assembler's rules. Under those rules
nothing counts before `max(1968, birth year + 22)`, and each odd year from
1997 is filled with the mean of its neighbours. The mask does not apply the
assembler's exclusions (incomplete domain, eligibility before 1979, empty
span, inconsistent chronology and low coverage;
`estimates/career.py:1581-1598`). For the cohorts used, `max(1968, birth year
+ 22)` is 1968 for everyone. The difference is exact and involves no PSID. A
run adds the PSID career product's values beside the masked EPUF values.
Survival to the PSID's observation years has no EPUF counterpart and is named
as a difference, not corrected.

Why report-only: the career product is observed PSID earnings with fixed
fill rules. It has no generator to hold out and no faithful-candidate null,
and its distance from EPUF is the bridge itself.

## 9. What is published, and what is not certified

A run that regenerates a gate-1 candidate reports each cell's 20-seed
estimate, its distance from EPUF, and the split of that distance into the
candidate's distance from the PSID and the PSID's distance from EPUF
(`report_candidate`, which returns no pass or fail). Tranche R reports the
career statistics beside the masked EPUF values. No run has been made.

Nothing is certified. In particular:

- no pass or fail, on any cell;
- careers, years without earnings by age 62, and the 35-year AIME;
- any year before 1998, and 2006;
- that the PSID agrees with EPUF. The bridge is published per cell.

## 10. Blindness and forking paths

**Order of commits.**

1. `eec910d6` holds the reader, operator, cell statistics, gate algebra,
   floor builder, their tests and the rules (sections 2-6 and 8 of this
   document). It was pushed on 2026-10-02 at 13:37 UTC, before any real-PSID
   value in EPUF units existed, and PR #509 opened on it.
2. The floor builder then ran once, at that commit. While reading its output
   the drafting session found a bug in the report-only career AIME (fork 1).
   It fixed the bug in `970a9db7` and rebuilt.
   `runs/epuf_gate_floors_v1_first_build.json` is the first build, frozen
   (SHA-256 `369bf5ec4e62c0eaa2f70702a9173188c87e84a5544bb4470826781c1847e378`).
   A test checks that its window cells, floors, partition and bites equal the
   rebuild's; only tranche R differs.
3. `ce8d5000` added the rebuilt artifact, the draft block and section 7.
   Neither artifact records its build time. The supplement records its own
   (2026-10-02 20:55 UTC).
4. The round-1 commit adds the referee report, the supplement, the frozen
   first build, the ruling and these corrections.

**Forks ledger.**

| # | Change after the first floor build | Partition before | Partition after | Why it is not a self-rescue |
|---|---|---|---|---|
| 1 | Career AIME ranks every year after 1950 through age 61, not only ages 22-61; the career-assembler mask starts at `max(1968, birth year + 22)` | `r6.men`, `r6.women` selected | unchanged | tranche R is report-only and enters no gated rule; the statute fixes the definition |
| 2 | Referee round 1: the gate does not lock; the two selected cells become report-only | `r6.men`, `r6.women` selected | nothing gated | it removes a pass-or-fail surface rather than rescuing one, and no rule or threshold was changed to reach it |

**Who had seen what at the rules commit.** The drafting session and the
design panel had seen EPUF-only values of every cell, and EPUF subsampled to
PSID scale. They had also seen gate 1's committed artifacts. Those show that
candidate 11's sex-pooled log autocorrelation is above the PSID reference at
two and four years and below it at ten, on all five seeds. No one had
computed a real-PSID value in EPUF units, a bridge, or any candidate value
under this gate's measurement.

**Before any run.** No candidate has been generated. Tranche R's PSID side
has not been computed.

**Strings this record supersedes.** The floor artifacts and the files they
bind to cannot be edited without breaking that binding, so a few of their
strings predate the ruling. `gate_partition.status` in the floor artifact
reads `lockable_pending_referee_round`, and its tranche R note says "computed
once, after lock". The docstring of `epuf_gate.tolerance` calls the formula
"the house formula". The block and this document supersede them: nothing is
pending a lock, and `k = 4` is not house precedent (section 4).

## 11. Considered and rejected

1. **EPUF-centred tolerance with no bridge.** A faithful candidate's pass
   probability falls toward zero as the bridge grows relative to the noise.
   `gate_w1` amendment 1 demoted ten cells for this.
2. **Subtracting the bridge.** EPUF cancels and the gate re-runs gate 1.
3. **A symmetric band `|G| <= |B| + t`.** It accepts overshoot past EPUF by
   the full bridge.
4. **Per-seed scoring with a 4-of-5 rule.** At 20 percent holdouts the
   per-seed noise is more than twice the 20-seed noise, which leaves almost no
   cell inside the caps.
5. **A floor from 20%/80% splits alone, divided by the square root of 20.** It
   omits the noise the seeds share. The two-term floor bounds that noise, and
   the bound is exact for a generator that draws from the true law.
   `tests/harness/test_epuf_gate.py::test_floor_prices_a_faithful_generator`
   shows by simulation that such a generator's 20-seed mean spreads about as
   widely as the two-term floor and well beyond the one-term floor.
6. **Gating the career product.** It is observed data, not a generator
   (section 8).
7. **Including 2006.** EPUF's 2006 worker count is 97.3 percent of the
   Supplement's from late posting (Compson 2012).
8. **A gated PSID-against-PSID leg in EPUF units.** It would keep the gate
   from being empty when bridges are large, but a gate named for EPUF should
   not pass on a comparison that leaves EPUF out. The model-against-PSID term
   is published in every run's decomposition instead.
9. **Random rounding in the operator.** It adds noise, and scored values
   would depend on a rounding seed.
10. **The planning documents' fixed bands** (one point on the share at the
    maximum, 0.05 on correlations; `docs/evaluation-and-model-selection.md`).
    They are not priced from a floor.
11. **Locking with the bite requirement restated after the result** (option
    (a)). Rejected in referee round 1 (section 7.5).

## 12. What a gate with bite would need

This surface cannot be rescued by retuning. The PSID's size sets the noise:
on 2,182 pairs of men and 2,376 of women with earnings in both years, the
1998-2004 rank correlation has a realised sigma of 0.025. Even with `k` chosen
so a faithful generator passes 95 percent of the time, a tolerance near two
sigmas would leave a 90 percent detection point near 0.08 below the PSID. And
every redesign of these cells is now informed by their bridges.

A fresh EPUF gate, under a new registration id, would need all of these
before its floor is built:

1. **Unseen ground.** Cells whose PSID-against-EPUF bridges no one has
   computed. On the current generator there are none. A generator that
   produced earnings for EPUF's earlier years would supply them. So would
   careers, where the tranche R statistics become scoreable; the PSID records
   earnings every year from 1968 to 1996.
2. **A consistent bite.** `k` set by a stated operating-characteristic rule,
   and every bite dosed above its cell's own 90 percent detection point,
   checked against EPUF subsampled to PSID scale before the build.
3. **A catch beyond gate 1.** A perturbation shown, before lock, to pass gate
   1's battery and fail the new gate.
4. **Bites under the gate's noise model**, with the noise the seeds share
   included, as the supplement now computes them.
5. **The smaller house details** found in round 1: events counted on the
   weakest band of a sex-level cell; panel digests for every scored seed;
   the repository's birth-year precedence; a build timestamp in the artifact;
   floor half-split seeds that do not reuse gate seeds; non-finite values
   stripped from every block of the artifact, not only the floor and bites.

## 13. Ceremony checklist

- [x] Proposal: this document, the floor artifact, the draft block
- [x] Adversarial referee round 1 (verdict AMEND)
- [x] Fixes: the supplement, the frozen first build, separate rules and build
  commits in the block, a pinned scoring path, corrected wording
- [x] Ruling: closed without lock; every cell report-only
- [x] Verification round 2 (verdict: merge after listed fixes, applied)
