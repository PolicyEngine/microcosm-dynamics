# gate_epuf registration (proposal): generated earnings histories against SSA's Earnings Public-Use File

- **Registration id**: `2026-10-02-epuf-covered-earnings`
- **Gate**: `gate_epuf` (new; not in `gates.yaml`)
- **Surface**: tranche G, the gate-1 generator's earnings on the four even
  reference years 1998-2004, by sex and birth cohort, scored against SSA's 2006
  Earnings Public-Use File (EPUF). Tranche R, the career statistics, is
  registered report-only.
- **Ceremony stage**: PROPOSAL (draft). This is the first step of the lock
  ceremony (proposal, adversarial referee, fixes, verification, ratify by
  merge, flip). **It edits no `gates.yaml` cell and no committed
  `runs/*.json`.** The proposed entry is
  `docs/design/gate_epuf_block_draft.yaml` with `locked: false`; the flip
  copies it into `gates.yaml` in a separate ratifying PR.
- **Class**: new gate, unlocked. No model has been scored against it.
- **Evidence base**: `runs/epuf_gate_floors_v1.json` (floors, bridges,
  partition, operating characteristic, bite demonstrations);
  `data/external/epuf_2006/` (provenance, SSA's documentation, published
  tables, disclosure constants); `runs/gate1_rank_knn_v5.json` (the gate-1 run
  whose generator this gate scores).

## 1. Summary

Gate 1 scores the model's generated earnings histories against held-out PSID
records. Experts who work with administrative earnings will ask how those
histories compare with SSA's own records. DYNASIM and MINT start from surveys
matched to SSA earnings, and CBOLT from the Continuous Work History Sample; all
three are confidential. EPUF is public: a 1 percent sample of Social Security
numbers issued before 2007, with year of birth, sex and capped taxable earnings
for each year from 1951 to 2006
(<https://www.ssa.gov/policy/docs/microdata/epuf/index.html>).

This proposal registers a gate that scores the gate-1 generator against EPUF.
Three facts shape it.

1. **The generator and EPUF overlap in four years.** The gate-1 generator
   redraws earnings on each held-out person's observed PSID periods, which are
   the even reference years 1998 to 2022 at ages 25 to 59
   (`scripts/run_gate1_candidate10.py:258-298`). EPUF ends in 2006, and its
   2005 and 2006 are short from late posting. The scoreable overlap is 1998,
   2000, 2002 and 2004. Nothing in the repository generates a career: the
   careers that benefit figures rest on are observed PSID earnings from 1968
   with rule-based fills (`src/populace_dynamics/estimates/career.py:964-1076`).
2. **The PSID itself sits at some distance from EPUF.** PSID labor income
   counts noncovered work, the gate-1 panel holds heads and spouses who stay
   in the survey, and earnings are reported, not filed. A generator trained on
   the PSID inherits that distance. A gate that demands agreement with EPUF to
   within sampling noise would fail every PSID-trained generator, and the
   better the generator copied the PSID the more surely it would fail.
3. **A 20-seed mean has noise that its seeds share.** Each seed scores
   generated values against the same realised PSID sample, so averaging over
   seeds removes only part of the noise.

The design that follows from these: score the mean over the gate's 20
registered seeds; accept a cell when the generated value lies between EPUF and
the PSID's own position, plus a tolerance priced from a real-data floor that
includes the shared noise; and gate a cell only when that whole acceptance
band stays inside a power cap, so that a pass always means "within the cap of
EPUF". Cells that cannot meet that are published with the reason.

The four career statistics the request named (years without earnings by age
62, rank persistence ten years apart, the share at the taxable maximum by age,
and the AIME under the 35-year rule) cannot be scored on generated histories,
because no generator produces careers. They are registered as tranche R,
report-only, with their EPUF reference values in the floor artifact.

## 2. What is scored

**Candidate.** Any generator that emits gate 1's candidate panel: for a
holdout drawn by `populace_dynamics.harness.panel.split_panel_by_person`
(`fraction=0.2`, seed `s`) from gate 1's filtered panel, the holdout's persons
on their observed periods with generated `earnings`. The first registered
candidate is the gate-1 passing generator (`runs/gate1_rank_knn_v5.json`,
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
calibration. A candidate that does is scored and labelled a calibration check.

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

The generator never sees sex: its inputs are age, period and earnings ranks,
and its levels are quantiles of sex-pooled age-by-period marginals
(`scripts/run_gate1_candidate10.py:557-562`). Gate 1 scores sex-pooled
moments. Cells by sex are therefore where this gate tests something gate 1
does not.

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
second term stands for the noise that averages down: who falls in each
holdout, each seed's draws and each seed's fit.

**Tolerance.** `t = round(mean|e_b| + 4 * sd|e_b|, 3)`, the house formula
(sd with `ddof=1`), with `k = 4` on every cell. `sigma` is the root mean
square of `e_b`.

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
   pairs.
3. `epuf_sampling_not_negligible`: EPUF's own sampling sd (50 random groups)
   exceeds 0.1 `sigma`.
4. `noise_exceeds_cap`: `t + 0.8416 sigma` exceeds the cap.
5. `bridge_exceeds_budget`: `|B| + t + 0.8416 sigma` exceeds the cap.

Rules 4 and 5 make the cap bind on the 80 percent power point, not on the
tolerance: a candidate whose distance from EPUF reaches the cap fails with
probability at least 0.8, and a pass certifies a distance below the cap.

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
reproduces that candidate's committed gate-1 artifact exactly.

## 6. Bite demonstrations

Each is a perturbation of the real PSID support, scored on the 20 gate
holdouts as a candidate would be, over 50 perturbation seeds. No candidate is
generated.

| Bite | Perturbation | Required of |
|---|---|---|
| `bd1` | With probability 0.10 (and, reported, 0.05) a person takes a same-sex, same-band donor's 1998-2002 earnings | persistence, if gated |
| `bd2` | Everyone takes the 1998-2002 path of a donor in the same band and 2004 class (no earnings, or decile of 2004 earnings), drawn from both sexes | reported |
| `bd2c` | As `bd2`, donors of the person's own sex: the control that isolates pooling the sexes | reported |
| `bd3` | In 1998-2002, half of each year's top 8 percent of positive earners move to a rank drawn uniformly from 0.5 to 0.92 | tail, if gated |
| `bd4` | Each positive 1998-2002 person-year becomes zero with probability 0.03 | participation, if gated |

The real gate-seed holdouts are also scored as a training copy and must pass.

## 7. Results of the floor build

*Filled by the floor build, which runs after the rules above are committed
and pushed (section 10).*

## 8. Tranche R: career statistics, report-only

Report-only, computed once in the post-lock run, never gated. The statistics
are the request's four, on annual capped histories at ages 22-61, by sex and
birth cohort (1930-1934, 1935-1939, 1940-1944: the cohorts whose whole window
lies inside 1951-2006):

- years without earnings (mean, quartiles, share with ten or more, share with
  all 40);
- Spearman correlations 1980 to 1990 and 1994 to 2004, among those positive in
  both years;
- share of positive person-years at the wage base, by age band;
- AIME under the 35-year rule through age 61 (quartiles, 90th percentile,
  share zero), matching `populace_dynamics.ss.statutory_aime.aime`.

The floor artifact holds their EPUF values twice: on EPUF as published, and
on EPUF masked the way the career assembler builds a PSID career (nothing
before 1968; each odd year from 1997 filled with the mean of its neighbours).
The difference is exact and involves no PSID: it is what those two rules
alone do to administrative careers. The post-lock run adds the PSID career
product's values beside the masked EPUF values. Survival to the PSID's
observation years has no EPUF counterpart and is named as a difference, not
corrected.

Why report-only: the career product is observed PSID earnings with fixed
fill rules. It has no generator to hold out and no faithful-candidate null,
and its distance from EPUF is the bridge itself. A career-completion model,
when one exists, becomes gate-eligible on these cells by amendment.

## 9. What a pass certifies

A pass certifies, for each gated cell and only those: the generated value's
distance from EPUF is below the cell's cap, and no larger than the PSID's own
distance plus noise.

Not certified, at the same prominence:

- careers, years without earnings by age 62, and the 35-year AIME;
- any year before 1998, and 2006;
- ages outside the support's range in the window, about 25 to 57;
- the forward earnings law of `gate_m6`, which this gate does not touch;
- that the PSID agrees with EPUF. The bridge is published per cell; a pass
  that rests on a large bridge says the generator is no worse than its source;
- levels by age, which the generator takes from PSID marginals.

## 10. Blindness and forking paths

**Order of commits.** The first commit of the pull request holds the reader,
operator, cell statistics, gate algebra, floor builder, their tests and
sections 1-6 and 8-13 of this document. It was pushed before any real-PSID
value in EPUF units existed. The second commit adds the floor artifact, the
draft block and section 7. The artifact records the first commit's sha and
the sha256 of each derivation file; a test fails if one changes afterwards.

**Who has seen what, at the first commit.** The drafting session and the
design panel saw: EPUF-only values of every cell; EPUF subsampled to PSID
scale; gate 1's committed artifacts, including that candidate 11's sex-pooled
log autocorrelation is above the PSID reference at two and four years and
below it at ten on all five seeds. No one had computed a real-PSID value in
EPUF units, a bridge, or any candidate value under this gate's measurement.

**After the floor build.** The bridges are then known, and with the gate-1
battery they suggest how the first candidate will score. That is why the
partition is mechanical and fixed first. Any later change to a rule is
recorded in a forks ledger in this document with the partition before and
after, and no cell may be redefined on account of its own bridge.

**Before lock.** No candidate is generated. Tranche R's PSID side is not
computed.

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
   omits the noise the seeds share, which
   `tests/harness/test_epuf_gate.py::test_floor_prices_a_faithful_generator`
   shows by simulation: a faithful generator's 20-seed mean spreads about as
   widely as the two-term floor and well beyond the one-term floor. The
   artifact records each cell's shared-noise share of the floor variance.
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

## 12. The lock flip (not in this pull request)

Ratification is by merge of a flip PR after an adversarial referee round and
a verification round. The flip:

1. copies `docs/design/gate_epuf_block_draft.yaml` into `gates.yaml` after
   `gate_m6`, with `locked: true`;
2. extends the gate-set allowlists in `tests/test_gates_derivations.py` and
   `tests/test_gate_w1_derivations.py`;
3. re-pins `CONTRACT_BLOB_LIVE` (`tests/test_gate_w1_candidate4_pin.py`) and
   runs `scripts/build_legacy_manifest.py --transition`;
4. registers the first run on issue #42 with the run script, the commit and
   a forecast.

The post-lock run regenerates candidate 11 on seeds 0-19, asserts exact
reproduction of `runs/gate1_rank_knn_v5.json`, scores the panels with
`populace_dynamics.harness.epuf_run.score_candidate`, computes tranche R, and
publishes the result whatever it is.

## 13. Ceremony checklist

- [x] **Proposal** (this document, the floor artifact, the draft block)
- [ ] Adversarial referee round
- [ ] Fixes
- [ ] Verification round
- [ ] Ratify by merge of the flip PR
- [ ] Registration of the first run on issue #42
