# Draft registration: tests for starting the projections from Microcosm's US population

**DRAFT. NOT POSTED.** This is the text proposed for a comment on [issue #42](https://github.com/PolicyEngine/microcosm-dynamics/issues/42). It is posted only after Max's go (decision d947) and after the independent review recorded on this pull request. Until then nothing in it is registered, and anything in it may change. The plan it serves is [`microcosm-start.md`](microcosm-start.md).

Placeholders: `N` is the next free registration number when posted (20 if nothing else is registered first). `<date>`, `<quote>`, `<commit>` and `<sha256>` are filled when posted.

---

**Registration N: tests for starting the projections from Microcosm's US population. Two gates (H1 and gate 3's first cells) and two report-only checks (W2 and A1), registered before any code, floor or candidate run exists, with H1's three candidates frozen here.**

A gate, in this repository, is a pass-or-fail test whose rules we publish before running it. A part of the model counts as tested only after it passes. A report-only check is published the same way, with no pass or fail.

Max authorized posting on `<date>` (decision d947): `<quote>`. The plan behind these tests is `docs/plans/microcosm-start.md` at `<commit>`, SHA-256 `<sha256>`. Code citations refer to `origin/master` at `<commit>`, with paths under `src/populace_dynamics/` unless a path says otherwise.

This is the first of several comments. It fixes:

- each test's question, held-out data, split, statistics, cells, tolerance rule and pass rule;
- H1's candidates and the rule for adopting one.

The two gates then lock separately:

- **H1:** floors and bite checks from real data, referee rounds, and Max's ratification of its multipliers lock it in `gates.yaml`. A second comment posts the registered commit and forecasts, and H1's candidates run once, together.
- **Gate 3:** it locks later, after the engine that would run it exists and passes its bite check, through its own lock comment (see "Gate 3", below).

Abbreviations:

- **Data sets:** PSID is the Panel Study of Income Dynamics. EPUF is SSA's 2006 Earnings Public-Use File. CPS is the Current Population Survey. PUF is the IRS Public Use File.
- **Benefit terms:** AIME and PIA are the average indexed monthly earnings and the primary insurance amount. QC is a quarter of coverage.
- **Methods:** QRF is a quantile regression forest.
- **This repository:** "the frame" is Microcosm's US cross-section. `EV` is the evidence folder `~/microcosm-launch-evidence/dynasim-parity-20260909`.

Terms:

- A **floor** is the gap between two disjoint samples of real data. It sets how far a result can move by chance.
- **Bite** is a check that a method known to be wrong fails the test, so the test can tell good from bad. That method is the **strawman**.
- A **partition** splits a test's cells, before anything is scored, into the ones that decide pass or fail and the ones only reported.
- A **Spearman correlation** is the correlation of ranks.
- The **effective sample size** (Kish) is the number of equally weighted people a weighted sample is worth.

### What these tests are for

Today the projections follow a PSID cohort. Starting them from the frame needs three things the model does not have: an earnings history for each person in the frame, a starting stock of beneficiaries whose PIAs are known, and income and wealth that age.

- **H1** tests the histories.
- **W2** checks the starting stock against SSA's records.
- **Gate 3's cells** test the projection's first year from the frame.
- **A1** reports how well income and wealth age.

### H1: earnings histories for a cross-section (gate)

**Question.** Given only what a cross-section observes in one year, does the procedure the plan deploys produce careers whose benefit-relevant features match real careers it has not seen?

**What a pass certifies.** The procedure as deployed:

1. PSID donors, matched by rank from one observed year.
2. Years the PSID lacks, filled by the procedure gate_epuf_fill certifies, or by the current rules if it certifies none.
3. Conversion to covered, capped shares of the wage base.

It is scored on SSA's records (arm E) and on the PSID (arm P). It does not certify the transfer of a rank from CPS or PUF records into the PSID, which W2 reports.

**The observable set.** For each person a candidate receives only:

- **both arms:** age (or birth year), sex, and earnings in the anchor year;
- **arm P only:**
  - marital status at the 2023 interview, and a link to a spouse in the arm;
  - whether the person reports being permanently disabled (the PSID's employment-status recode, `data/disability.py`);
  - annual hours of work in the anchor year;
  - whether the person is self-employed.

On the frame these become, in order: `A_MARITL` with the spouse line; `is_disabled`; `WKSWORK` times `HRSWK` (weeks worked times usual weekly hours); and `is_self_employed`. Two are not the same concept on both sides, and both are labeled:

- the PSID's "permanently disabled" employment status against the CPS's disability items;
- the PSID's annual hours against weeks times usual hours.

The PSID readers for hours and self-employment do not exist yet and are built before lock.

**Left out of the observable set:**

- **Education.** No Microcosm US release checked carries it. If the frame gains it, an amendment registered before any further run adds it, with data not yet used.
- **Occupation and class of worker.** Their codes differ between the PSID and the frame across years.
- **Year of US entry.** The PSID holds too few immigrants to learn from. Histories for immigrants are cut at entry instead (plan, section 5.4).

**Anchor rank.** Each person's anchor rank is computed within the scored population's own anchor-year distribution for their sex and five-year age band:

- arm E: H1-TEST's 2006 distribution;
- arm P: all of arm P's 2022 distribution, weighted.

That mirrors the frame, which ranks people within itself.

**Draws and seeds.** A candidate returns earnings for every year of the person's career before the anchor year, for each of 20 draw seeds (7300 to 7319).

- Draws come from counter-based uniforms keyed by the draw seed, the person id and the year, so a person's draw does not depend on which other persons are scored.
- Every fitted component (H-A's participation model, H-C's forests, the fill refit) is seeded from `numpy.random.default_rng([7400, arm, seed, component])`. The arm code is 1 for E and 2 for P. The seed is 0 in arm E and the split seed in arm P. Component codes are listed in the second comment.

#### Arm E: SSA's earnings records

- **Data.** EPUF 2006 through `populace_dynamics.data.epuf`, as pinned by pull request #509: capped, covered earnings for 1951–2006, sex and year of birth.
- **Split (new, fixed now).** Each person's position `u` is the first eight bytes, big-endian, of the SHA-256 of `populace_dynamics.history_attachment.split.v1|` followed by the decimal person id, divided by 2^64.
  - TRAIN is `u` below 0.6, DEV is 0.6 to 0.8, and TEST is 0.8 and above.
  - The salt differs from gate_epuf_fill's, so H1's TEST is not the set gate_epuf_fill reads and publishes. No EPUF statistic has been computed under this split.
  - TEST is read only through an accessor that refuses until `gates.yaml` locks gate_h1.
- **Two configurations, both scored on H1-TEST.**
  - **Deployed (gated).**
    - The donors are PSID heads and spouses. The 2006 anchor rank is applied in the PSID's 2006 cell, the same transfer the frame makes into the PSID's 2022 cell.
    - Years the PSID lacks are filled by the procedure gate_epuf_fill certifies (or the current rules, if it certifies none), refit on H1-TRAIN so that no fitted parameter has seen an H1-TEST person. Which procedure that is follows from gate_epuf_fill's verdict, so H1's registered run waits for it, and the second comment names the procedure by gate_epuf_fill's run artifact. The frame itself uses gate_epuf_fill's own fit, not this refit.
    - **Overlap with gate_epuf_fill's selection.** That procedure was designed and selected on gate_epuf_fill's TRAIN and DEV. Under its different salt, those hold about 80 percent of H1-TEST's people, and about a fifth of H1-TEST is in gate_epuf_fill's published TEST. As in arm P, the scored people are not independent of the procedure's selection, though no fitted parameter has seen them.
    - Output is converted to shares of each year's wage base, capped at 1.
  - **Method only (report-only).** The same candidate with H1-TRAIN donors. The gap between the two configurations shows how much of any miss comes from the PSID itself rather than the method.
- **What may be learned from.** The PSID, and H1-TRAIN. No model fitted on EPUF persons outside H1-TRAIN may be used. That excludes gate_epuf_fill's own fitted fills; its procedure is refit instead.
- **Persons.** TEST persons with sex coded 1 or 2, born 1937 to 1984 (aged 22 to 69 in 2006).
- **Given.** Sex, birth year, and 2006 earnings as a share of the 2006 wage base. Zero is allowed. Shares at the cap (exactly 1) are ranked by a uniform draw within the tied mass, keyed by the person id, so ties break the same way for every candidate. The proportion at the cap is a round-1 referee's citation of gate_epuf_fill's DEV results (see Disclosure).
- **Hidden and returned.** Every year from the later of 1951 and the year the person turned 16, through 2005, as shares of each year's wage base, each in [0, 1].
- **Statistics per person**, computed the same way on real and returned careers:
  - `T35`: the mean of the person's 35 highest years of capped earnings through 2006, each indexed to 2006 by the national average wage index. Zeros count when fewer than 35 years are positive.
  - `PIAx`: the PIA formula with 2006 bend points applied to `T35` / 12. This is a proxy, not a statutory PIA.
  - `Z`: the share of years with zero earnings from age 22 (or 1951) through 2005. A person with fewer than three such years enters no `Z` cell, and how many such people there are is counted. The 22–29 band therefore scores people aged 25 to 29.
  - `C`: the share of positive years at the taxable maximum.
  - `Q40`: whether the person has 40 or more QCs by the end of 2006.
    - From 1978 on, QCs come from the repository's QC amounts (`min_benefit_track_m/coverage.py:60-70`).
    - Before 1978, EPUF has no quarterly earnings, so a year counts `min(4, floor(earnings / $50))` QCs. That is an upper bound under the rule of one quarter per $50 of wages in a quarter, and it is labeled as a convention.
- **Statistics per cell:**
  - the 10th, 25th, 50th, 75th and 90th percentiles of `PIAx`;
  - the means of `Z`, `C` and `Q40`;
  - the Spearman correlation of 2006 earnings with `T35`, among people positive in 2006;
  - the Spearman correlations of 2006 earnings with 2004, 2002 and 1996 earnings, among people positive in both years: the two-, four- and ten-year lags, which check persistence near and far from the anchor.
- **Cells.**
  - **Main block:** sex by age in 2006 (22–29, 30–39, 40–49, 50–59, 60–69), with 12 statistics each.
  - **Zero-anchor block:** the `PIAx` percentiles and `Z` for people with zero 2006 earnings. EPUF records no deaths or emigration, so this group includes people who died or left, while the frame's zero earners are all alive and resident. The block is labeled with that difference.
- **Score.** As gate_epuf_fill scores a fill.
  - For a correlation, the gap is the returned value minus the true value.
  - For every other cell, the gap is the log of the returned value over the true value.
  - The returned value is the cell's mean over the 20 draw seeds. Both are computed on the same TEST persons.
- **Floor and tolerance.** As gate_epuf_fill prices its cells (`harness/epuf_fill_gate.py`, docstring item 4, on branch `epuf-career-fill-20261003`).
  - For each group, 200 replicates draw two disjoint samples of `n` persons from that group's DEV population, using the stream `default_rng([5100, group index, 200, n])`.
  - `n` is the effective sample size (Kish, from household weights) of the frame pinned at lock, among the frame's persons the group counts. For the zero-anchor block, that means the frame's zero earners of that sex and age.
  - `sigma` is the root mean square of `[m(A) - m(B)] / sqrt(2)` over the replicates.
  - The tolerance is `tau = K x sigma`, with **proposed K = 1**: the procedure may move a cell by at most one frame-size sampling error. Max ratifies K at lock.

#### Arm P: the PSID

- **Data.** The PSID family files through `data/family.py`'s earnings panel: head and spouse labor income for income years 1968 to 2022.
- **Persons.** Heads and spouses in the 2023 wave, aged 25 to 64 in 2022, with a positive 2023 weight.
- **Bite part and split.** Family units are those of the 2023 wave.
  - **The bite part:** the 20 percent of units whose salted hash (`populace_dynamics.history_attachment.psid_bite.v1|` followed by the unit id, as in arm E) falls below 0.2. It is never held out in a scored seed.
  - **The scored seeds:** in each of seeds 100 to 104, a unit outside the bite part is held out when the hash of `populace_dynamics.history_attachment.psid_split.v1|`, the seed, `|` and the unit id falls below 0.2. Spouses therefore fall together.
- **Not independent of earlier selection.** Gate 1 drew its person splits over seeds 0 to 19 from this same panel and selected the rank-kNN method and its blend constant (0.1) on it (`runs/gate1_rank_knn_v5.json`, `model.inner_validation`).
  - Arm P is a fresh split of data the method was tuned on.
  - Gate 1 scored only 1998–2022 at ages 25–59, pooled. Arm P adds years before 1998, whole careers, cells by marital status and by disability, and couples.
- **What may be learned from.** The units not held out in that seed (the bite part included), and H1-TRAIN of EPUF.
- **Given.** The arm-P observable set, with 2022 as the anchor year.
- **Hidden and returned.** Labor income in dollars for every year the PSID recorded for the person, from the later of age 22 and 1968, through 2020. Scoring uses recorded years only, as gate 1 does; years the career assembler filled or set to zero are not scored.
- **Statistics per person**, on real and returned careers:
  - `M`: the mean of labor income indexed by the national average wage index over the person's recorded years from age 22 through 2020, zeros included;
  - `Zr`: the share of those recorded years at ages 25 to 44 with zero earnings.

  A person with fewer than four recorded years enters neither statistic, and how many such people there are is reported.
- **Statistics per cell:**
  - the 25th, 50th and 75th percentiles of `M`;
  - the mean of `Zr`;
  - the Spearman correlation of 2022 earnings with `M`, among people positive in 2022;
  - the Spearman correlations of log earnings two, four and ten years apart, pooled over every recorded pair through 2022 positive in both years.
- **Cells:**
  - sex by marital status at the 2023 interview (married, widowed, divorced or separated, never married);
  - sex by disability status at the 2023 interview;
  - a couple block, for married couples both in the arm: the median of the lower spouse's `M` over the higher spouse's, and the share of couples where that ratio is below one half. "Lower" is decided within each set of careers, real or returned.
- **Report-only blocks:**
  - **Education.** Sex by education group (less than 12 years, 12, 13–15, 16 or more), plus the ratio of median `M` for 16 or more years to 12 years by sex. No candidate sees education, so the block measures what leaving it out costs. It needs a PSID education reader, which is built before lock.
  - **The forward law's starting state.** The forward law reads two things from the past: realized start-year earnings, and a permanent-rank estimate `u_w` fitted over the person's whole positive history (`engine/forward_earnings.py:697-739`, mixed in at 0.1 at line 1533; the earnings two years back are kept if observed and left missing otherwise, and the first draws do not condition on them, lines 1444-1463). This block holds the certified law's fitted parameters and age marginals fixed and recomputes each person's `u_w` from that person's positive years, real or returned, through 2020 plus the 2022 anchor. It reports the Spearman correlation and the mean absolute difference of the two estimates by sex and age band.
- **Score.** For each seed, the cell statistic on returned careers, averaged over the 20 draw seeds, minus the statistic on the real careers of the same held-out people.
- **Floor and tolerance.** As gate 1 prices its geometry thresholds (`gates.yaml:140-143, 323-333`, each derivation checked by `tests/test_gates_derivations.py`).
  - The floor draws pairs of disjoint real samples, each the size of one seed's held-out cell, from the panel, and records `|m(A) - m(B)|` on the cell's scale.
  - The tolerance is `tau = floor mean + k x floor SD`, with **proposed k = 2**. Max ratifies k at lock.
- **Pass.** A gating cell passes if `|score| <= tau`. A seed passes if every gating cell passes. Arm P passes if at least 4 of the 5 seeds pass.

#### Partition, bite and lock

- **Which cells gate.** Fixed at the floor build, before any candidate runs. A cell gates if it meets gate_epuf_fill's sufficiency rules (its proposal, section 6) and, in arm E, a false-fail budget.
  - **Sufficiency:** its true value is finite, and positive for a log-ratio cell; its floor is finite and positive; and in at least 95 percent of floor replicates the smaller sample of the pair has at least 20 events.
  - **False-fail budget (arm E).** Each sufficient cell has a faithful-noise ratio `r = sqrt(1 + 1/20) x sqrt(n / N_TEST)`. That is the standard deviation, in units of `sigma`, of the gap of a procedure drawing from the true conditional law (gate_epuf_fill's argument, its section 5). Its chance of failing that cell is `p = 2 x (1 - Phi(K / r))`. Cells enter the gating set in order of increasing `r` while the sum of their `p` stays at or below 0.05. The floor build reports every `r`, `p` and the sum.

  Every other cell is reported without a verdict. The partition and its reasons are committed with the floors.
- **Bite.** Before lock, the strawman runs in each arm, in the deployed configuration. The strawman is gate 1's failed baseline: the backward QRF on next-period earnings and age (`scripts/run_gate1_baseline.py`).
  - **Arm E:** it is scored on DEV.
  - **Arm P:** it is fitted on the 80 percent of the bite part whose hash of `populace_dynamics.history_attachment.psid_bite_inner.v1|` and the unit id is 0.2 or above, and scored on the other 20 percent. No scored seed's held-out unit is read.
  - **Margin:** in each arm the strawman must fail at least one gating cell by more than 2 tau, gate_epuf_fill's margin (`BITE_MULTIPLE = 2.0`). In arm P the bite is scored on a sample about a quarter the size of a seed's held-out set, so its `tau` comes from a floor built at the bite sample's own size, by the same rule. If the strawman does not fail, H1 does not lock without an amendment.
- **Gate pass.** H1 passes if arm E's deployed configuration and arm P both pass.

#### Candidates, frozen here, run together

Every constant below is fixed by this comment. The fill procedure is not a free choice: it follows from gate_epuf_fill's verdict, as stated in arm E. The second comment adds only the code commit, the component codes, the SHA-256 of any fitted artifact, and the name of that fill procedure. All three candidates and the strawman are scored in one registered run, after lock, and their results are published together. No candidate's result is seen before another's is fixed.

1. **H-A, rank-kNN.** Gate 1's candidate 11, unchanged in its draw and distances (`runs/gate1_rank_knn_v5.json`, `model`): k = 25, distance weights 1, 0.5 and 0.25, the fixed blend of 0.1 for the permanent rank, and the zero-anchor regime.
   - Earnings distributions are sex-specific.
   - It steps one year where the donor data are annual and two where they are biennial.
   - It covers ages 16 to 69.
2. **H-B, rank-kNN with marital strata.** H-A with donors restricted, in arm P, to the person's sex and marital group.
   - A stratum with fewer than 250 donor records falls back to sex alone, and the fallback is counted.
   - Arm E has no marital status, so there H-B is H-A, and the two differ only in arm P.
   - No other constant is added.
3. **H-C, a QRF with the predictors H1 can align across the PSID and the frame.** A backward chain of populace-fit's regime-gated QRF at its default hyperparameters: 100 trees, `zero_atol = 1e-6`, no leaf cap (as `runs/gate1_qrf_baseline_v1.json`, `model.hyperparameters`).
   - It predicts each earlier year from the next year's earnings, age, sex and anchor-year earnings.
   - In arm P it also uses marital status, disability status, annual hours and self-employment.

**Adoption rule.**

- **Order:** H-A if it passes H1; otherwise H-B if it passes; otherwise H-C if it passes.
- **None passes:** no history procedure is certified. Any later use of histories on the frame is labeled uncertified, and no text may call it tested.
- **Lower-order passes:** a passing candidate lower in the order is reported, not adopted.

### Gate 3: the first projected year (gate)

`gates.yaml` names gate 3 for near-term outputs judged against administrative publications and gives it no cells (`gates.yaml:2898-2905`). This registration proposes its first cells and rules. It locks separately from H1, after the engine adapter exists and passes the bite check below, through its own comment here.

**Question.** Started from the frame in its year, does the projection engine move the beneficiary population over one year the way SSA's records moved?

**Data.**

- SSA's Annual Statistical Supplement editions with December data for the start year and the year after, tables 5.B1 (retired workers: number, average PIA and average monthly benefit, by age and sex) and 5.D1 (disabled workers by sex).
- The evidence folder holds a capture of the 2023 edition, whose layout these cells follow (`EV/ssa-supplement-2023/MANIFEST.tsv`).
- Each edition is captured with URL, date, size and SHA-256 before the run.
- If the later edition is not published when the engine is ready, the run waits.

**Cells.**

- Retired workers by sex and age group (62–64, 65–69, 70–74, 75–79, 80 and over): number and average monthly benefit.
- Disabled workers by sex: number and average monthly benefit.
- Claim-age cells are excluded. The engine draws claim ages from SSA's own award tables, so those cells would score the engine against its own input.

**Concepts.**

- **`F0`** is the frame's value in the start year. It counts people with receipt during the calendar year, and their annual amount divided by 12.
- **`P1`** is the projection's value a year on, on the same concept: people with receipt during the next calendar year, and their annual payments divided by 12, averaged over 20 draws.
- **`S0` and `S1`** are SSA's December values for the two years.

**Statistic.** The signed growth gap `g = ln(P1 / F0) - ln(S1 / S0)`.

- **What cancels.** The frame's concept (receipt during the year) differs from SSA's (current-payment status in December). Comparing growth cancels that difference to the extent it is stable over one year.
- **What does not cancel.** Errors in the frame's makeup that change how many people die, are widowed or claim, such as the share married, feed into growth. Gate 3 scores them along with the engine.

**Tolerance.** `delta = 0.01 + 2 x s`.

- `s` is the standard deviation of `g` over a household bootstrap of the frame, 500 replicates, each projected with the same draws, computed within the registered run.
- **Both constants are proposals** for Max to ratify at gate 3's lock.

**Partition.** It is fixed before any projection, from a 500-replicate household bootstrap of the start-year frame alone.

- A cell whose `ln(F0)` has a bootstrap standard deviation above 0.05 is report-only.
- The partition script writes only the standard deviations, never `F0` itself.
- No projected value enters the partition.

**Pass.** Every gating cell has `|g| <= delta`.

**Bite.** It runs before gate 3's lock, on an invented frame of the real frame's size, with the engine adapter as built.

- **The wrong engines:** one with no mortality, and one that awards no new benefits. Each is compared with the faithful engine on the same invented frame and draws, through `d = ln(P1_wrong / P1_faithful)`.
- **The margin:** each wrong engine must miss at least one gating cell by `|d| > 2 x delta_inv`. Here `delta_inv = 0.01 + 2 x s_inv`, and `s_inv` is the standard deviation of `ln(P1 / F0)` over a 500-replicate household bootstrap of the invented frame.
- **If it fails:** gate 3 does not lock.

**What it does not score.** Long-run dynamics, reform responses, or the frame's own level errors, which W2 reports.

### W2: the starting stock against SSA's records (report-only)

- **Question.** Do the frame's beneficiaries, with PIAs inferred from their benefits, match SSA's December counts and averages for the start year?
- **Data.**
  - The frame pinned at lock.
  - The Supplement edition with December data for the frame's year: tables 5.B1, 5.D1 and 5.G1 (dually entitled retired workers by PIA and sex).
- **Cells.**
  - 5.B1's age groups by sex: number, average monthly benefit and average PIA.
  - 5.D1 by sex: number and average monthly benefit.
  - 5.G1 by sex: number.

  Dual entitlement is identified by a proxy, a person with two reasons for receipt in the CPS (`RESNSS1`, `RESNSS2`), and labeled as one.
- **Statistic.** `ln(frame / SSA)` per cell, three ways:
  - all records;
  - records outside the PUF-support channel;
  - records without the synthetic split of Social Security components.

  Average PIAs are reported twice: inferred from the frame's benefits, and computed from generated histories.
- **Inferred PIAs.** These come for retired and disabled workers only. A spouse's or survivor's linked worker PIA is not inferred in this version:
  - such beneficiaries keep their benefit as state;
  - the linked PIA is marked missing;
  - any rule that would need it is counted as unsupported for them.
- **Named limits.** Each limit is reported per cell, with the count of records it touches where the frame can identify them. Where it cannot, the limit is reported as unquantified.
  - The frame counts receipt during a calendar year, and SSA counts December current-payment status.
  - Amounts may be net of the Medicare Part B premium. This is unquantified.
  - Receipt can begin partway through the year. This is unquantified.
  - Dually entitled people's retirement amounts can include a spouse's excess.
  - Benefits for income years 2022–2024 can reflect the windfall elimination provision and government pension offset, which the Social Security Fairness Act repealed for benefits after December 2023.
- **Bridge.** The distributions of the frame's anchor-year earnings by sex, age band, source year and channel are reported beside the PSID's 2022 distributions. That shows where the rank anchor carries levels between data sets.
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

- **Before lock.** No candidate reads held-out data before lock. Floors read real data only and score no candidate.
- **One run.** H1's three candidates and its strawman run once, together, after gate_epuf_fill's verdict.
  - One disclosed re-execution is allowed, only for an infrastructure failure before scoring begins, and only after a comment here.
  - Nobody reads the failed attempt's outputs.
  - A failure after scoring begins, or a failed re-execution, ends this registration for H1.
- **Refusals.** If a refusal check fails (wrong data hashes, a dirty tree, a pointer that is not a comment here), the run writes no statistic and the refusal is reported here.
  - If any statistic was computed before the refusal, the next registration discloses that it was discarded unread.
- **No projection from the real frame before gate 3 locks.** The engine adapter (plan task T8) is built and tested on invented data. The first projection of the real frame is gate 3's registered run.
- **No-drop.** Every cell, seed and statistic is computed and kept, including undefined values with their reason.
- **Publication.**
  - Every artifact is committed under `runs/` unedited, whatever it shows.
  - Within 24 hours of a run, a comment here posts its times, its exit status and the SHA-256 of the artifact, with no statistic.
  - The results then follow this repository's merge rules for a gate run.
- **Amendments** are public and prospective, and cannot rescue a run already scored.
- **Frame pin.** The frame release is fixed at lock by repository, revision, file and SHA-256.
  - Changing it is an amendment.
  - The tolerances that depend on its effective sample size are re-derived before any further run.

### Platform

- **H1, A1 and the floors.** They run locally, through the `heavy` compute queue. EPUF is public. The PSID files stay on this machine, as for every gate.
- **W2 and gate 3.** They read the frame, which carries values imputed from the PUF, and run locally unless Max rules otherwise for this registration.
  - Registration 19's Modal ruling (d806) covers only that analysis.
  - d093, which is parked, asks only whether restricted PUF inputs may go to Modal.

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

### Who chose what

- **The drafter** chose every design element in this comment: the orchestrating session, Claude Code, Opus 5.5. That covers:
  - the tests and their arms;
  - the cells and statistics;
  - the proposed multipliers;
  - the candidates and the adoption order;
  - the partition and bite rules;
  - the platform.
- **The independent referees** shaped it: the review rounds below changed the split, the candidates' freezing, gate 3's statistic and bite, and arm E's deployed configuration.
- **Max's ruling** authorizes posting (d947, quoted above). He ratifies the multipliers at lock.

### Disclosure: who has seen what

**The drafter.** It drafted this text on 2026-10-04 and read:

- **gate 1:** the artifacts `gate1_qrf_baseline_v1`, `gate1_qrf_latent_perm_v1` and `v2`, `gate1_qrf_structural_v1`, `gate1_splice_v1` and `v2`, `gate1_rank_v1`, `gate1_rank_kernel_v1`, `gate1_rank_knn_v1` and `gate1_rank_knn_v5`: their descriptions, verdicts and per-seed autocorrelation checks;
- **other gates:** the verdicts of gates 2, 2b, 2c, m4, w1 and m6;
- **exercise 1:** the cohort block of `runs/replication_urban2010_cola_v1.json`;
- **registrations:** Registrations 13, 18 and 19;
- **planning:** the NASI meeting's transcript and slides, and the PlanGraph plan.

**gate_epuf_fill and gate_epuf.**

- The drafter read lines 1–200 of gate_epuf_fill's registration proposal: sections 1 to 4.2, which hold person counts and no EPUF statistic.
- It read sections 5 to 7.3, its rules. Section 5 quotes DEV statistics: masked units per DEV person, 2.45 for men 22–29 and 4.51 for men 22–74.
- It did not open section 10a or any `runs/epuf_fill_*` artifact.
- A text search of `runs/epuf_gate_supplement_v1.json` displayed several per-seed estimates of gate_epuf's PSID and EPUF rank-persistence cells.

**The frame.** On three cached frame releases, the drafter read structure only. The three are Registration 19's release, the one gate w1 pins, and the 8 July dense build. It read:

- the person and household column lists;
- record counts by source year and support channel, and the age codes;
- weight shares by channel, and the effective sample size from household weights.

The script and its output are `docs/plans/microcosm-start-evidence/frame_structure.py` and `frame_structure.txt`. It summarized no income, benefit, asset or other outcome variable.

**SSA tables.** The drafter read the titles of the captured 2023 Supplement tables 5.B1, 5.D1 and 5.G1, and no values.

**Referees.**

- Round 1's referee read gate_epuf_fill's section 10a. It cited the share of men's positive EPUF shares at the cap (about 10 percent), and arm E's tie rule answers that citation.
- Both referees read the frame-structure evidence and Registrations 13, 18 and 19.
- Neither opened microdata or a sealed comparator file.

**Not seen.**

- No EPUF record and no PSID record.
- No EPUF statistic under H1's new split.
- No frame outcome.
- No sealed comparator file listed in `EV/RESTRICTED-FILES.md`.

**Research lanes.** Five Subfleet research lanes were briefed (`~/reviews/microcosm-start-plan-20261004/briefs/`) and cancelled before they started, when every Codex lane was on hold. The drafter did that reading itself.

**No forecast** is registered here. The second comment carries one for each candidate, written before the run.

### Pre-registration review

Independent of the drafter. Reports are in `~/reviews/microcosm-start-plan-20261004/review/`.

- **Round 1** (Subfleet lane, Opus 5.5; `review-r1.md`): CHANGES REQUIRED, with 3 blocking, 16 major and 19 minor findings. Each was answered (`response-r1.md`).
- **Round 2** (Subfleet lane, Opus 5.5; `review-r2.md`): CHANGES REQUIRED, with 6 major findings (N1–N6) and 14 minor ones. Each was answered (`response-r2.md`).
- **Round 3** (Subfleet lane, Opus 5.5; `review-r3.md`): APPROVE AFTER LISTED FIXES. Five findings were edited in (`response-r3.md`). A delta check of the changed lines follows: `<verdict and path, filled when posted>`.

### What comes next

1. **Readers.** Build the readers H1 and A1 need: PSID hours, self-employment and education, and PSID wealth for 1999–2021.
2. **H1 lock.**
   - Build H1's floors and partition from real data only, and run H1's bite checks.
   - Two referee rounds independent of the drafter.
   - Max's ratification of K and k, then H1's lock in `gates.yaml`.
3. **H1 run.** After gate_epuf_fill's verdict, the second comment posts the registered commit, component codes, artifact hashes, the fill procedure that verdict selects, and the forecasts. Then H1's one run.
4. **Gate 3 lock.** Once the engine adapter exists:
   - fix gate 3's partition from the start-year bootstrap;
   - run its bite check on the invented frame;
   - Max ratifies its constants, and gate 3 locks through its own comment here.

   Its registered run follows.
5. **W2 and A1** run as their inputs are ready, each after a comment here naming its commit.
