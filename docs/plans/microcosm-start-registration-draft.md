# Draft registration: tests for starting the projections from Microcosm's US population

**DRAFT. NOT POSTED.** This is the text proposed for a comment on [issue #42](https://github.com/PolicyEngine/microcosm-dynamics/issues/42). It is posted only after Max's go (decision d947) and after the independent review recorded on this pull request. Until then nothing in it is registered, and anything in it may change. The plan it serves is [`microcosm-start.md`](microcosm-start.md).

Placeholders: `N` is the next free registration number when posted (20 if nothing else is registered first). `<date>`, `<commit>` and `<sha256>` are filled when posted.

---

**Registration N: tests for starting the projections from Microcosm's US population. Two gates (H1 and gate 3's first cells) and two report-only checks (W2 and A1), registered before any code, floor or candidate run exists, with H1's three candidates frozen here.**

A gate, in this repository, is a pass-or-fail test whose rules we publish before running it. A part of the model counts as tested only after it passes. A report-only check is published the same way but has no pass or fail.

Max authorized posting on `<date>` (decision d947). The plan behind these tests is `docs/plans/microcosm-start.md` at `<commit>`, SHA-256 `<sha256>`. Code citations refer to `origin/master` at `<commit>`, with paths under `src/populace_dynamics/` unless a path says otherwise.

This is the first of several comments. It fixes:

- each test's question, held-out data, split, statistics, cells, tolerance rule and pass rule;
- H1's candidates and adoption rule.

Next come the floors, built from real data only, then referee rounds, then Max's ratification of the tolerance multipliers, then the lock in `gates.yaml`. A second comment then posts the registered commit, and H1's candidates run once, together.

Abbreviations: PSID is the Panel Study of Income Dynamics. EPUF is SSA's 2006 Earnings Public-Use File. CPS is the Current Population Survey. PUF is the IRS Public Use File. AIME and PIA are the average indexed monthly earnings and the primary insurance amount. QRF is a quantile regression forest. QC is a quarter of coverage. "The frame" is Microcosm's US cross-section. `EV` is the evidence folder `~/microcosm-launch-evidence/dynasim-parity-20260909`.

Three terms recur:

- A **floor** is the gap between two disjoint samples of real data. It sets how far a result can move by chance.
- **Bite** is a check that a method known to be wrong fails the test, so the test can tell good from bad.
- A **partition** splits a test's cells, before anything is scored, into the ones that decide pass or fail and the ones that are only reported.

### What these tests are for

Today the projections follow a PSID cohort. Starting them from the frame needs three things the model does not have:

- an earnings history for each person in the frame;
- a starting stock of beneficiaries whose PIAs are known;
- income and wealth that age.

H1 tests the histories. W2 checks the starting stock against SSA's records. Gate 3's cells test the projection's first year from the frame. A1 reports how well income and wealth age.

### H1: earnings histories for a cross-section (gated)

**Question.** Given only what a cross-section observes in one year, does a method produce careers whose benefit-relevant features match real careers it has not seen?

**The observable set.** For each person a candidate receives only:

- **Both arms:** age (or birth year), sex, and earnings in the anchor year.
- **Arm P only:**
  - marital status in the anchor year, and a link to a spouse in the arm;
  - whether the person reports being permanently disabled (the PSID's employment-status recode, `data/disability.py`);
  - annual hours of work in the anchor year;
  - whether the person is self-employed.

  The frame carries each of these (`is_disabled`; `weeks_worked` with `hours_worked_last_week`; `is_self_employed`). The PSID readers for hours and self-employment do not exist yet and are built before lock.

**Left out of the observable set:**

- **Education.** No Microcosm US release checked carries it. If the frame gains it, an amendment registered before any further run adds it, with data not yet used.
- **Occupation and class of worker.** Their codes differ between the PSID and the frame across years.
- **Year of US entry.** The PSID holds too few immigrants to learn from. Histories for immigrants are cut at entry instead (plan, section 5.4).

A candidate returns earnings for every year of the person's career before the anchor year, for each of 20 draw seeds (7300 to 7319). Its draws come from counter-based uniforms keyed by the draw seed, the person id and the year. A person's draw therefore does not depend on which other persons are scored.

#### Arm E: SSA's earnings records

- **Data.** EPUF 2006 through `populace_dynamics.data.epuf`, as pinned by pull request #509: capped, covered earnings for 1951–2006, sex and year of birth.
- **Split (new, fixed now).** Each person's position `u` is the first eight bytes, big-endian, of the SHA-256 of `populace_dynamics.history_attachment.split.v1|` followed by the decimal person id, divided by 2^64.
  - TRAIN is `u` below 0.6, DEV is 0.6 to 0.8, and TEST is 0.8 and above.
  - The salt differs from gate_epuf_fill's, so H1's TEST is not the set gate_epuf_fill reads and publishes.
  - No EPUF statistic has been computed under this split.
  - TEST is read only through an accessor that refuses until `gates.yaml` locks gate_h1.
- **What a candidate may learn from.** H1-TRAIN persons, and any PSID data. No model fitted on EPUF persons outside H1-TRAIN may be used. That rules out gate_epuf_fill's fills, which learn from its own TRAIN part.
- **Persons.** TEST persons with sex coded 1 or 2, born 1937 to 1984 (aged 22 to 69 in 2006).
- **Given.** Sex, birth year, and 2006 earnings as a share of the 2006 wage base. Zero is allowed. Shares at the cap (exactly 1) are ranked by a uniform draw within the tied mass, keyed by the person id, so ties break the same way for every candidate.
- **Hidden and returned.** Every year from the later of 1951 and the year the person turned 16, through 2005, as shares of each year's wage base, each in [0, 1].
- **Statistics per person**, computed the same way on real and returned careers:
  - `T35`: the mean of the person's 35 highest years of capped earnings through 2006, each indexed to 2006 by the national average wage index. Zeros count when fewer than 35 years are positive.
  - `PIAx`: the PIA formula with 2006 bend points applied to `T35` / 12. This is a proxy, not a statutory PIA.
  - `Z`: the share of years from age 22 (or 1951) through 2005 with zero earnings.
  - `C`: the share of positive years at the taxable maximum.
  - `Q40`: whether the person has 40 or more QCs by the end of 2006.
    - From 1978 on, QCs come from the repository's QC amounts (`min_benefit_track_m/coverage.py:60-70`).
    - Before 1978, EPUF has no quarterly earnings, so a year counts `min(4, floor(earnings / $50))` QCs. This is an upper bound, labeled as a convention.
- **Statistics per cell:**
  - the 10th, 25th, 50th, 75th and 90th percentiles of `PIAx`;
  - the means of `Z`, `C` and `Q40`;
  - the Spearman correlation of 2006 earnings with `T35`, among people positive in 2006;
  - the Spearman correlations of 2006 earnings with 2004, 2002 and 1996 earnings, among people positive in both years. These are the two-, four- and ten-year lags. The two-year lag is the state the forward law starts from.
- **Cells.**
  - The main block is sex by age in 2006 (22–29, 30–39, 40–49, 50–59, 60–69), with 12 statistics each.
  - A second block repeats the `PIAx` percentiles and `Z` for people with zero 2006 earnings.
  - EPUF records no deaths or emigration, so this zero-anchor group includes people who died or left, while the frame's zero earners are all alive and resident. The block is labeled with that difference.
- **Score.** As gate_epuf_fill scores a fill. For a correlation, the gap is the returned value minus the true value. For every other cell it is the log of the returned value over the true value. The returned value is the cell's mean over the 20 draw seeds. Both are computed on the same TEST persons.
- **Floor and tolerance.** As gate_epuf_fill prices its cells (`harness/epuf_fill_gate.py`, docstring item 4, on branch `epuf-career-fill-20261003`).
  - For each group, 200 replicates draw two disjoint samples of `n` persons from DEV.
  - `n` is the effective sample size (Kish, from household weights) of the frame pinned at lock, in that sex and age group.
  - `sigma` is the root mean square of `[m(A) - m(B)] / sqrt(2)` over the replicates.
  - The tolerance is `tau = K x sigma`, with **proposed K = 1**: a method may move a cell by at most one frame-size sampling error. Max ratifies K at lock.
- **What it does not test.** Whether PSID earnings carry over to SSA's concept. Arm E's candidates learn from EPUF donors. The PSID-to-SSA gap is gate_epuf's report-only comparison (pull request #509).

#### Arm P: the PSID

- **Data.** The PSID family files through `data/family.py`'s earnings panel: head and spouse labor income, income years 1967 to 2022.
- **Persons.** Heads and spouses in the 2023 wave, aged 25 to 64 in 2022, with a positive 2023 weight.
- **Split.** By 2023 family unit, so spouses fall together. For each of seeds 100 to 104, 20 percent of family units are held out.
- **Not independent of earlier selection.** Gate 1 drew its person splits over seeds 0 to 19 from this same panel, and selected the rank-kNN method and its blend constant (0.1) on it (`runs/gate1_rank_knn_v5.json`, `model.inner_validation`).
  - Arm P is a fresh split of data the method was tuned on.
  - Gate 1 scored only 1998–2022 at ages 25–59, pooled. Arm P adds years before 1998, whole careers, cells by marital status and by disability, and couples.
- **What a candidate may learn from.** The family units not held out in that seed, and H1-TRAIN of EPUF.
- **Given.** The arm-P observable set, with 2022 as the anchor year.
- **Hidden and returned.** Labor income in dollars for every year the PSID recorded for the person, from age 22 (or 1968) through 2020. Scoring uses recorded years only, as gate 1 does. Years the career assembler filled or set to zero are not scored.
- **Statistics per person**, on real and returned careers:
  - `M`: the mean of labor income indexed by the national average wage index over the person's recorded years from age 22 through 2020, zeros included;
  - `Zr`: the share of those recorded years at ages 25 to 44 with zero earnings.

  A person with fewer than four recorded years enters neither statistic, and how many such people there are is reported.
- **Statistics per cell:**
  - the 25th, 50th and 75th percentiles of `M`;
  - the mean of `Zr`;
  - the Spearman correlation of 2022 earnings with `M`, among people positive in 2022;
  - the Spearman correlations of log earnings two, four and ten years apart, over recorded pairs positive in both years.
- **Cells:**
  - sex by marital status in 2023 (married, widowed, divorced or separated, never married);
  - sex by disability status in 2023;
  - a couple block, for married couples both in the arm: the median of the lower spouse's `M` over the higher spouse's, and the share of couples where that ratio is below one half. "Lower" is decided within each set of careers, real or returned.
- **Education block (report-only).**
  - Its cells are sex by education group (less than 12 years, 12, 13–15, 16 or more), plus the ratio of median `M` for 16 or more years to 12 years by sex.
  - No candidate sees education, so the block measures what leaving it out costs.
  - It needs a PSID education reader, which is built before lock.
- **Floor and tolerance.** As gate 1 prices its geometry thresholds (`gates.yaml:140-143, 323-333`, each derivation checked by `tests/test_gates_derivations.py`).
  - The floor draws pairs of disjoint real samples, each the size of one seed's held-out cell, from the panel, and records `|m(A) - m(B)|` on the cell's scale.
  - The tolerance is `tau = floor mean + k x floor SD`, with **proposed k = 2**. Max ratifies k at lock.
- **Score and pass.** For each seed, the score is the cell statistic on returned careers minus the statistic on the real careers of the same held-out people.
  - A gating cell passes if `|score| <= tau`.
  - A seed passes if every gating cell passes.
  - Arm P passes if at least 4 of the 5 seeds pass.

#### Partition, bite and lock

- **Which cells gate.** Fixed at the floor build, before any candidate runs, by gate_epuf_fill's sufficiency rules (its proposal, section 6). A cell gates if all of these hold:
  - its true value is finite, and positive for a log-ratio cell;
  - its floor is finite and positive;
  - in at least 95 percent of floor replicates, the smaller sample of the pair has at least 20 events.

  Every other cell is reported without a verdict.
- **What a faithful method's noise looks like.** In arm E the score compares the same people's real and returned careers. A method drawing from the true conditional law has a gap whose standard deviation is about `sqrt(1 + 1/20) x sqrt(n / N_TEST) x sigma` (gate_epuf_fill's argument, its section 5). The floor build reports this noise ratio for each cell, and a cell where it exceeds 0.5 is report-only.
- **Bite.** Before lock, gate 1's failed baseline is retrained on each arm's training data. That baseline is the backward QRF on next-period earnings and age (`scripts/run_gate1_baseline.py`).
  - Arm E's check runs on DEV, and arm P's on seed 100's training complement.
  - In each arm, the baseline must fail at least one gating cell by more than 2 tau. That is the margin gate_epuf_fill uses (`BITE_MULTIPLE = 2.0`).
  - If it does not, H1 does not lock without an amendment.
- **Gate pass.** H1 passes if arm E and arm P both pass.

#### Candidates, frozen here, run together

Every constant below is fixed by this comment. The second comment adds only the code commit and the SHA-256 of any fitted artifact. All three candidates and the strawman are scored in one registered run, after lock, and their results are published together. No candidate's result is seen before another's is fixed.

1. **H-A, rank-kNN.** Gate 1's candidate 11, unchanged in its draw and distances (`runs/gate1_rank_knn_v5.json`, `model`): k = 25, distance weights 1, 0.5 and 0.25, the fixed blend of 0.1 for the permanent rank, and the zero-anchor regime.
   - **Anchor:** the person's earnings rank within five-year age band and sex.
   - **Earnings distributions:** sex-specific.
   - **Steps:** one year where the donor data are annual, two where they are biennial.
   - **Ages:** 16 to 69.
   - **Donors:** H1-TRAIN of EPUF in arm E; the training families in arm P.
2. **H-B, rank-kNN with marital strata.**
   - In arm P, H-A with donors restricted to the person's sex and anchor-year marital group.
   - A stratum with fewer than 250 donor records falls back to sex alone, and the fallback is counted.
   - Arm E has no marital status, so there H-B is H-A, and the two differ only in arm P.
   - No other constant is added.
3. **H-C, a QRF with every predictor both data sets carry.** A backward chain of populace-fit's regime-gated QRF at its default hyperparameters: 100 trees, `zero_atol = 1e-6` and no leaf cap, as in `runs/gate1_qrf_baseline_v1.json`, `model.hyperparameters`.
   - **Both arms:** it predicts each earlier year from the next year's earnings, age, sex and anchor-year earnings.
   - **Arm P only:** it also uses marital status, disability status, annual hours and self-employment.

**Strawman for bite: S.** Gate 1's baseline, as above.

**Adoption rule.**

- Adopt H-A if it passes H1. Otherwise adopt H-B if it passes, and otherwise H-C if it passes.
- If none passes, no history method is certified. Any later use of histories on the frame is labeled uncertified, and no text may call it tested.
- A passing candidate lower in the order is reported, not adopted.

### Gate 3: the first projected year (gated)

`gates.yaml` names gate 3 for near-term outputs judged against administrative publications and gives it no cells (`gates.yaml:2898-2905`). This registration proposes its first cells.

- **Question.** Started from the frame in its year, does the projection engine move the beneficiary population over one year the way SSA's records moved?
- **Data.**
  - **Source:** SSA's Annual Statistical Supplement editions with December data for the start year and the year after.
  - **Tables:** 5.B1 (retired workers: number, average PIA and average monthly benefit, by age and sex) and 5.D1 (disabled workers by sex). The evidence folder holds a capture of the 2023 edition, whose layout these cells follow (`EV/ssa-supplement-2023/MANIFEST.tsv`).
  - **Capture:** each edition is captured with URL, date, size and SHA-256 before the run.
  - **Timing:** if the later edition is not published when the engine is ready, the run waits.
- **Cells.**
  - Retired workers by sex and age group (62–64, 65–69, 70–74, 75–79, 80 and over): number and average monthly benefit.
  - Disabled workers by sex: number and average monthly benefit.
  - Claim-age cells are excluded, because the engine draws claim ages from SSA's own award tables and would be scored against its own input.
- **Statistic.** The signed growth gap `g = ln(P1 / F0) - ln(S1 / S0)`.
  - `F0` and `P1` are the frame's value in the start year and the projection's a year on, averaged over 20 draws.
  - `S0` and `S1` are SSA's values for the same two years.
  - The frame records Social Security received during a calendar year, while SSA counts people in current-payment status in December. Because the statistic compares growth, it cancels that concept gap to the extent the gap is stable over one year.
- **Tolerance.** `delta = 0.01 + 2 x s`. Here `s` is the standard deviation of `g` over a household bootstrap of the frame (500 replicates), each replicate projected with the same draws. **Both constants are proposals** for Max to ratify at lock.
- **Partition, fixed before any run.** It comes from a 500-replicate household bootstrap of the start-year frame alone.
  - A cell whose `ln(F0)` has a bootstrap standard deviation above 0.05 is report-only.
  - No projected value enters the partition.
  - Gate 3's constants and partition are fixed before W2's first run, which reveals `F0 / S0`.
- **Pass.** Every gating cell has `|g| <= delta`.
- **Bite.** Before lock, two deliberately wrong engines run: one with no mortality, and one that awards no new benefits.
  - They run on an invented frame of the real frame's size, and on the real start-year values `F0`. No projected value is read.
  - Each must fail at least one gating cell by more than 2 delta, using `delta` from the bootstrap. Otherwise gate 3 does not lock.
- **What it does not score.** Long-run dynamics, reform responses, or the frame's own level errors, which W2 reports.

### W2: the starting stock against SSA's records (report-only)

- **Question.** Do the frame's beneficiaries, with PIAs inferred from their benefits, match SSA's December counts and averages for the start year?
- **Data.**
  - The frame pinned at lock.
  - The Supplement edition with December data for the frame's year: tables 5.B1, 5.D1 and 5.G1 (dually entitled retired workers by PIA and sex).
- **Cells.**
  - 5.B1's age groups by sex: number, average monthly benefit and average PIA.
  - 5.D1 by sex: number and average monthly benefit.
  - 5.G1 by sex: number. Dual entitlement is identified by a proxy, a person with two reasons for receipt in the CPS (`RESNSS1`, `RESNSS2`), and labeled as one.
- **Statistic.** `ln(frame / SSA)` per cell, three ways:
  - all records;
  - records outside the PUF-support channel;
  - records without the synthetic split of Social Security components.

  Average PIAs are reported twice: inferred from the frame's benefits, and computed from generated histories.
- **Named limits, reported per cell.** Each carries the count of records it touches, where the frame can identify them:
  - The frame counts receipt during a calendar year, and SSA counts December current-payment status.
  - Amounts may be net of the Medicare Part B premium.
  - Receipt can begin partway through the year.
  - Dually entitled people's retirement amounts can include a spouse's excess.
  - A survivor or spouse benefit cannot be inverted without the other worker's claim age and the beneficiary's own benefit.
  - Benefits for income years 2022–2024 can reflect the windfall elimination provision and government pension offset, which the Social Security Fairness Act repealed for benefits after December 2023.
- **Bridge.** The frame's anchor-year earnings distributions by sex and age band are reported beside the PSID's 2022 distributions, by channel. That shows where the rank anchor carries levels from one data set to another.
- **No pass band.** Microcosm calibrates Social Security dollars by type but not beneficiary counts (Registration 19), so counts and average PIAs are held out from its calibration. Any later pass rule needs an amendment registered before a further run.

### A1: income and wealth aging (report-only)

- **Question.** Applied to PSID families, how far does the plan's aging rule miss what the PSID recorded four years later?
- **The rule.** Each item grows with the baseline's index, and each unit keeps its rank within its cell.
  - Household items such as net worth rank among households, within the reference person's sex and five-year age band and household type (couple or single).
  - Person items rank among persons within sex and five-year age band.
  - Ranks inside a zero mass break by a uniform draw keyed by the unit's id.
- **Data.**
  - PSID family wealth (`WEALTH1`) and the income items exercise 2 reads, for families observed in both waves of each four-year pair from 1999 to 2021.
  - The repository reads wealth only for waves 2005–2013 (`cohorts/age67.py:94-98`), so the readers for the other waves are built before the run.
  - The rule fits nothing, so no family is held out.
  - Deaths and widowhood are taken as the PSID recorded them, so the check isolates the rule.
- **Cells.** By the reference person's age group (45–54, 55–64, 65–74, 75 and over):
  - the median change in log net worth, among families positive in both waves;
  - the share staying in the same net-worth quintile;
  - the share with zero or negative net worth four years on;
  - among families with no pension income at the start, the share with some four years on;
  - among recipients in both waves, the median log change in pension income.
- **Statistic and floor.** The rule's value minus the PSID's, beside a floor from pairs of disjoint halves of real families.
- **No pass band.** A1 becomes a gate only through an amendment registered before any further run, on waves or data not yet used.

### Rules

- **No peeking before lock.** No candidate reads held-out data before lock. Floors read real data only and score no candidate.
- **One run.** H1's three candidates and its strawman run once, together. One disclosed re-execution is allowed, only for an infrastructure failure before scoring begins, and only after a comment here.
- **No projection from the real frame before gate 3 locks.** The engine adapter (plan task T7) is built and tested on invented data. The first projection of the real frame is gate 3's registered run.
- **No-drop.** Every cell, seed and statistic is computed and kept, including undefined values with their reason. Every artifact is committed under `runs/` whatever it shows.
- **Amendments** are public and prospective, and cannot rescue a run already scored.
- **Frame pin.** The frame release is fixed at lock by repository, revision, file and SHA-256. Changing it is an amendment, and the tolerances that depend on its effective sample size are re-derived before any further run.

### Platform

- **H1, A1 and the floors** run locally under the `heavy` admission gate. EPUF is public. The PSID files stay on this machine, as for every gate.
- **W2 and gate 3** read the frame, which carries values imputed from the PUF. They run locally unless Max rules otherwise for this registration.
  - The general question for PUF-derived files is parked (d093).
  - Registration 19's Modal ruling (d806) covers only that analysis.

### Topology

- **Code** (none exists yet):
  - `harness/history_attachment_gate.py` for H1;
  - `frame_start/` for the frame reader, starting stock and engine adapter;
  - `scripts/build_gate_h1_floors.py`;
  - `scripts/run_gate_h1_registered.py`, which runs every candidate.

  Tests use invented data only.
- **Refusals.**
  - H1's TEST accessor refuses until `gates.yaml` locks gate_h1.
  - Every scored entry point refuses a pointer that is not a comment on this issue, a commit that is not the full SHA of a clean HEAD, and an existing output.
  - The frame reader refuses the real frame's hash outside a registered entry point, as Registration 19's population code does.

### Disclosure: who has seen what

**Drafter.** This text was drafted on 2026-10-04 and 2026-10-05 by the orchestrating session (Claude Code, Opus 5.5). It read:

- **Gate 1:** `gate1_qrf_baseline_v1`, `gate1_qrf_latent_perm_v1` and `v2`, `gate1_qrf_structural_v1`, `gate1_splice_v1` and `v2`, `gate1_rank_v1`, `gate1_rank_kernel_v1`, `gate1_rank_knn_v1` and `gate1_rank_knn_v5`, covering their descriptions, verdicts and per-seed autocorrelation checks.
- **Other gates:** the verdicts of gates 2, 2b, 2c, m4, w1 and m6.
- **Exercise 1:** the cohort block of `runs/replication_urban2010_cola_v1.json`.
- **Registrations** 13, 18 and 19.
- **gate_epuf_fill:**
  - lines 1–200 of its registration proposal (sections 1 to 4.2, which hold person counts but no EPUF statistic), and sections 5 to 7.3 (its rules);
  - it did not open section 10a or any `runs/epuf_fill_*` artifact.
- **gate_epuf:** a text search of `runs/epuf_gate_supplement_v1.json` displayed several per-seed estimates of gate_epuf's PSID and EPUF rank-persistence cells.
- **Planning sources:** the NASI meeting's transcript and slides, and the PlanGraph plan.

**Frame structure.** On three cached frame releases (Registration 19's, the one gate w1 pins, and the 8 July dense build) it read:

- the person and household column lists;
- record counts by source year and support channel, and the age codes;
- weight shares by channel and the effective sample size from household weights.

The script and its output are `docs/plans/microcosm-start-evidence/frame_structure.py` and `frame_structure.txt`. It summarized no income, benefit, asset or other outcome variable.

**SSA tables.** It read the titles of the captured 2023 Supplement tables 5.B1, 5.D1 and 5.G1, and no values.

**Not seen.**

- No EPUF record and no PSID record.
- No EPUF statistic under H1's new split.
- No frame outcome.
- No sealed comparator file listed in `EV/RESTRICTED-FILES.md`.

**Research lanes.** Five Subfleet research lanes were briefed (`~/reviews/microcosm-start-plan-20261004/briefs/`) and cancelled before they started, when every Codex lane was on hold. The drafter did that reading itself.

**No forecast** is registered here. The second comment carries one for each candidate, written before the run.

### Pre-registration review

Each review is independent of the drafter. Reports are in `~/reviews/microcosm-start-plan-20261004/review/`.

- **Round 1** (Subfleet lane, Opus 5.5; `review-r1.md`): CHANGES REQUIRED, with 3 blocking, 16 major and 19 minor findings. This text answers each one; the answers are listed in `response-r1.md`.
- **Round 2:** `<verdict and path, filled when posted>`.

### What comes next

1. Build the readers H1 and A1 need: PSID hours, self-employment and education, and PSID wealth for 1999–2021.
2. Build the floors and run the bite checks, all from real data only: H1's two arms, gate 3's partition from the start-year bootstrap, and A1's floors.
3. Two referee rounds independent of the drafter.
4. Max's ratification of K, k and gate 3's constants, then the lock in `gates.yaml`.
5. The second comment: the registered commit, the artifact hashes and the forecasts. Then the one run.
