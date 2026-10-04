# Draft registration: tests for starting the projections from Microcosm's US population

**DRAFT. NOT POSTED.** This is the text proposed for a comment on [issue #42](https://github.com/PolicyEngine/microcosm-dynamics/issues/42). It is posted only after Max's go (queued as a decision) and after the independent review recorded on this pull request. Until then nothing in it is registered, and anything in it may change. The plan it serves is [`microcosm-start.md`](microcosm-start.md).

Placeholders: `N` is the next free registration number when posted (20 if nothing else is registered first). `dXXX` is the decision that authorizes posting. `<commit>` and `<sha256>` are filled when posted.

---

**Registration N: tests for starting the projections from Microcosm's US population. Registered before any code, floor or candidate for them exists. One gated test with two arms (H1), one gated set of cells for gate 3, and two report-only checks (W2, A1).**

A gate, in this repository, is a test we register publicly before running it. A part of the model counts as tested only after it passes. "Report-only" means we publish the result with no pass or fail.

Max authorized posting on `<date>` (decision `dXXX`). The plan behind these tests is `docs/plans/microcosm-start.md` at `<commit>`, SHA-256 `<sha256>`.

This is the first of several comments. This one fixes each test's question, held-out data, split, statistics, cells, tolerance rule and pass rule. Floors come next, from real data only, then referee rounds and Max's ratification of the tolerance multipliers, then the lock in `gates.yaml`. Each candidate is then registered in its own comment, frozen before its one scored run.

Abbreviations: PSID is the Panel Study of Income Dynamics. EPUF is SSA's 2006 Earnings Public-Use File. CPS is the Current Population Survey. AIME and PIA are the average indexed monthly earnings and the primary insurance amount. QRF is a quantile regression forest. "The frame" is Microcosm's US cross-section. `EV` is the evidence folder `~/microcosm-launch-evidence/dynasim-parity-20260909`.

### What these tests are for

Today the projections follow a PSID cohort. Starting them from the frame instead needs three things the model does not have: an earnings history for each person in the frame, a starting stock of beneficiaries whose PIAs are known, and income and wealth that age. H1 tests the histories. W2 checks the starting stock against SSA's records. Gate 3's cells test the projection's first year from the frame. A1 reports how well income and wealth age.

### H1: earnings histories for a cross-section (gated)

**Question.** Given only what a cross-section observes in one year, does a method produce careers whose benefit-relevant features match real careers it has not seen?

**What a candidate receives.** For each person, only this observable set:

- age (or birth year) and sex;
- earnings in the anchor year;
- in the PSID arm only: marital status in the anchor year and a link to a spouse in the same arm.

Education is not in the set, because no Microcosm US release checked for the plan carries it. If the frame gains it, an amendment registered before any further run adds it, with fresh seeds.

A candidate returns earnings for every year of the person's career before the anchor year, for generation seeds 0 to 4.

**What a candidate may learn from.** In the EPUF arm, EPUF's TRAIN part and any PSID data. In the PSID arm, the PSID families not held out in that seed, and EPUF's TRAIN part. Nothing else from either data set.

#### Arm E: SSA's earnings records

- **Data.** EPUF 2006 through `populace_dynamics.data.epuf`, as pinned by pull request #509: capped, covered earnings for 1951–2006, sex and year of birth.
- **Split.** The one gate_epuf_fill fixed before computing any EPUF statistic: SHA-256 of `populace_dynamics.epuf_fill.split.v1|` and the decimal person id, first eight bytes over 2^64; TRAIN below 0.6, DEV from 0.6 to 0.8, TEST from 0.8 (`harness/epuf_fill_gate.py`, `split_part`, on branch `epuf-career-fill-20261003`). H1 builds its floors and partition on DEV and scores on TEST. TEST is read only through an accessor that refuses until `gates.yaml` locks gate_h1. Gate_epuf_fill's own reading of TEST comes first and publishes fill statistics for odd and pre-career years; no H1 candidate or floor uses them.
- **Persons.** TEST persons with sex coded 1 or 2, born 1937 to 1984 (aged 22 to 69 in 2006).
- **Given.** Sex, birth year and 2006 earnings as a share of the 2006 wage base. Zero is allowed.
- **Hidden and returned.** Every year from the later of 1951 and the year the person turned 16, through 2005, as shares of each year's wage base, each in [0, 1].
- **Statistics per person**, computed the same way on real and returned careers:
  - `T35`: the mean of the person's 35 highest years of capped earnings through 2006, each indexed to 2006 by the national average wage index (zeros count when fewer than 35 years are positive);
  - `PIAx`: the PIA formula with 2006 bend points applied to `T35` / 12 (a proxy, not a statutory PIA);
  - `Z`: the share of years from age 22 (or 1951) through 2005 with zero earnings;
  - `C`: the share of positive years at the taxable maximum;
  - `Q40`: whether the person has 40 or more quarters of coverage by the end of 2006, under the repository's quarter-of-coverage rule.
- **Statistics per cell**: the 10th, 25th, 50th, 75th and 90th percentiles of `PIAx`; the means of `Z`, `C` and `Q40`; the Spearman correlation of 2006 earnings with `T35` among people positive in 2006; and the Spearman correlation of 1996 with 2006 earnings among people positive in both.
- **Cells.** Sex by age in the anchor year: 22–29, 30–39, 40–49, 50–59, 60–69 (10 groups, 10 statistics each). A second block repeats the `PIAx` percentiles and `Z` for people with zero anchor earnings, by sex and age group, because their histories come without an earnings anchor.
- **Tolerance.** For each cell, a materiality threshold: `tau = K x s`, where `s` is the standard error the frame's own sample carries for that statistic. `s` is estimated on DEV from 200 pairs of disjoint samples, each the size of the effective sample (Kish) of the frame pinned at lock in that sex and age group, as the standard deviation of their difference divided by the square root of 2. **Proposed K = 1**, the reading of materiality gate_epuf_fill proposes for its fills: a method may move a cell by at most one frame-size sampling error. Max ratifies K at lock.
- **Score.** The cell statistic on returned careers, averaged over the five generation seeds, minus the same statistic on the real careers of the same TEST persons.
- **Pass.** Arm E passes if every gated cell's score is within its tolerance. Each seed's scores are published too.

#### Arm P: the PSID

- **Data.** The PSID family files through `data/family.py`'s earnings panel: head and spouse labor income, income years 1967 to 2022.
- **Persons.** Heads and spouses in the 2023 wave, aged 25 to 64 in 2022, with a positive 2023 weight.
- **Split.** By 2023 family unit, so spouses fall together. For each of seeds 100, 101, 102, 103 and 104, 20 percent of family units are held out. Gate 1 uses seeds 0 to 19; none is reused.
- **Given.** The observable set above, with 2022 labor income as the anchor.
- **Hidden and returned.** Labor income for every year the PSID recorded for the person, from age 22 (or 1968) through 2020. Scoring uses recorded years only, as gate 1 does; years the career assembler filled or set to zero are not scored.
- **Statistics per person**, on real and returned careers:
  - `M`: the mean of labor income indexed by the national average wage index over the person's recorded years from age 22 through 2020, zeros included;
  - `Zr`: the share of those recorded years at ages 25 to 44 with zero earnings.
  A person with fewer than four recorded years enters neither; their number is reported.
- **Statistics per cell**: the 25th, 50th and 75th percentiles of `M`; the mean of `Zr`; the Spearman correlation of 2022 earnings with `M`; and the Spearman correlation of log earnings ten years apart over recorded pairs.
- **Cells.** Sex by marital status in 2023 (married, widowed, divorced or separated, never married). A couple block, for married couples both in the arm: the median of the lower spouse's `M` over the higher spouse's, and the share of couples where that ratio is below one half.
- **Education block (report-only).** Sex by education group (less than 12 years, 12, 13–15, 16 or more), plus the ratio of median `M` for 16 or more years to 12 years by sex. No candidate sees education, so this block measures what leaving it out costs. It needs a PSID education reader, which the repository does not have yet.
- **Tolerance.** As gate 1 prices its battery: a floor from pairs of disjoint real samples, each the size of one seed's held-out set, drawn from the panel, and `tau = floor mean + k x floor SD`. **Proposed k = 2.** Max ratifies k at lock.
- **Score.** For each seed, the cell statistic on returned careers minus the statistic on the real careers of the same held-out people.
- **Pass.** A seed passes if every gated cell passes. Arm P passes if at least 4 of the 5 seeds pass.

#### Partition, bite and lock

- **Gated or report-only.** Decided before any candidate is scored, by two rules. A cell gates if a faithful generator would pass it with probability at least 0.95, estimated from pairs of disjoint real samples the size of the scored cell (arm E: the TEST cell, drawn from DEV; arm P: one seed's held-out cell, drawn from the panel), and if its floor rests on at least 200 people per side. Every other cell is report-only. The partition and its reasons are committed with the floors.
- **Bite.** Gate 1's failed baseline (the backward QRF on next-period earnings and age, `scripts/run_gate1_baseline.py`), retrained on each arm's training data, must fail H1. If it passes, H1 has no bite and does not lock without an amendment.
- **Gate pass.** H1 passes if arm E and arm P both pass.

#### Candidates

Each is registered in its own comment before its one scored run, with every constant fixed. They run in this order:

1. **H-A, rank-kNN.** Gate 1's candidate 11, unchanged in its draw and distances (`runs/gate1_rank_knn_v5.json`, `model`), anchored on the observable set's earnings rank within age band and sex, with sex-specific earnings distributions, one-year steps where the donor data are annual, and ages 16 to 69.
2. **H-B, rank-kNN with covariates.** H-A with donors restricted to the person's sex and a distance term for marital status. Its weight is fixed in its registration.
3. **H-C, QRF with every predictor.** A backward chain of populace-fit's regime-gated QRF that predicts each earlier year from the next year's earnings, age, sex, anchor-year earnings and marital status. It is a registered comparison, not a candidate for use, unless it passes and H-A does not.

### Gate 3: the first projected year (gated)

`gates.yaml` names gate 3 for near-term outputs judged against administrative publications and gives it no cells (`gates.yaml:2898-2905`). This registration proposes its first cells.

- **Question.** Started from the frame in December of its year, does the projection engine move the beneficiary population the way SSA's records moved over the next year?
- **Data.** SSA's Annual Statistical Supplement editions with December data for the start year and the year after: tables 5.B1 (retired workers: number, average PIA and average monthly benefit, by age and sex) and 5.D1 (disabled workers by sex). The repository captured the 2023 edition's layout (`EV/ssa-supplement-2023/MANIFEST.tsv`). Each edition is captured with URL, date, size and SHA-256 before the run. If the later edition is not published when the engine is ready, the run waits.
- **Cells.** Retired workers by sex and age group (62–64, 65–69, 70–74, 75–79, 80 and over): number, average monthly benefit. Disabled workers by sex: number, average monthly benefit. Claim-age cells are excluded, because the engine draws claim ages from SSA's own award tables and would be scored against its input.
- **Statistic.** The drift: `d = |ln(P1 / S1)| - |ln(F0 / S0)|`, where `F0` is the frame's value in the start year, `S0` and `S1` are SSA's values for the start year and the next, and `P1` is the projection's value a year on, averaged over 20 draws. The frame records Social Security received during a calendar year, while SSA counts people in current-payment status in December; the drift statistic cancels that concept gap to the extent it is stable over one year.
- **Tolerance.** `delta = 0.01 + 2 x s`, where `s` is the standard error of `ln(P1 / S1)` from a household bootstrap of the projected population (500 replicates). **Both constants are proposals** for Max to ratify at lock.
- **Pass.** Every gated cell's drift is within its tolerance. A cell whose `s` exceeds 0.05 is report-only.
- **What it does not score.** Long-run dynamics, reform responses, or the frame's own level errors, which W2 reports.

### W2: the starting stock against SSA's records (report-only)

- **Question.** Do the frame's beneficiaries, with PIAs inferred from their benefits, match SSA's December counts and averages for the start year?
- **Data.** The frame pinned at lock; the Supplement edition with December data for the frame's year, tables 5.B1, 5.D1 and 5.G1 (dually entitled retired workers by PIA and sex).
- **Cells.** Table 5.B1's age groups by sex: number, average monthly benefit, average PIA; 5.D1 by sex: number, average monthly benefit; 5.G1 by sex: number.
- **Statistic.** `ln(frame / SSA)` per cell, three ways: all records, records outside the PUF-support channel, and records without the synthetic split of Social Security components. Average PIAs are reported twice: inferred from the frame's benefits, and computed from generated histories. The frame counts receipt during a calendar year and SSA counts December current-payment status, a named concept gap.
- **No pass band.** Microcosm calibrates Social Security dollars by type but not beneficiary counts (Registration 19), so counts and average PIAs are held out from its calibration. Any later pass rule needs an amendment registered before a further run.

### A1: income and wealth aging (report-only)

- **Question.** Applied to PSID families, how far does the plan's aging rule (each item grows with the baseline's index, and each person keeps their rank within sex and five-year age band) miss what the PSID recorded four years later?
- **Data.** PSID family wealth (`WEALTH1`) and the income items exercise 2 reads, for families observed in both waves of each four-year pair from 1999 to 2021. The rule fits nothing, so no family is held out. Deaths and widowhood are taken as the PSID recorded them, so the check isolates the rule.
- **Cells.** By the head's age group (45–54, 55–64, 65–74, 75 and over): the median change in log net worth among families positive in both waves; the share staying in the same net-worth quintile; the share with zero or negative net worth four years on; among families with no pension income at the start, the share with some four years on; among recipients in both waves, the median log change in pension income.
- **Statistic and floor.** The rule's value minus the PSID's, beside the floor from pairs of disjoint real halves.
- **No pass band.** It becomes a gate only through an amendment registered before any further run, with fresh seeds.

### Rules

- **No candidate reads held-out data before lock.** Floors read real data only and score no candidate.
- **One shot per candidate.** One disclosed re-execution is allowed, only for an infrastructure failure before scoring begins, and only after a comment here.
- **No-drop.** Every cell, seed and statistic is computed and kept, including undefined values with their reason. Every artifact is committed under `runs/` whatever it shows.
- **Amendments** are public, prospective, and cannot rescue a run already scored.
- **Frame pin.** The frame release is fixed at lock by repository, revision, file and SHA-256. Changing it is an amendment.

### Topology

- **Code** (none exists yet): `src/populace_dynamics/harness/history_attachment_gate.py` for H1; `src/populace_dynamics/frame_start/` for the frame reader, starting stock and engine adapter; `scripts/build_gate_h1_floors.py`; one `scripts/run_gate_h1_candidate_<id>.py` per candidate. Tests use invented data only.
- **Refusals.** The H1 TEST accessor refuses until `gates.yaml` locks gate_h1. Every scored entry point refuses a pointer that is not a comment on this issue, a commit that is not the full SHA of a clean HEAD, and an existing output.

### Disclosure: who has seen what

- **Drafter.** This text was drafted by the orchestrating session (Claude Code, Opus 5.5) on 2026-10-04. It read committed run artifacts (gate 1's baseline and candidate 11, the verdicts of gates 2, 2b, 2c, m4, w1 and m6, and the cohort block of `runs/replication_urban2010_cola_v1.json`), Registration 19, gate_epuf_fill's proposal on its branch, and the NASI meeting's transcript and slides.
- **Frame structure.** On three cached frame releases (Registration 19's, the one gate w1 pins and the 8 July dense build) it read the column lists and tabulated record counts by source year and support channel, the age codes, weight shares by channel and the effective sample size from household weights (`docs/plans/microcosm-start-evidence/frame_structure.py` and its output). It summarized no income, benefit, asset or other outcome variable.
- **Not seen.** No EPUF record, no PSID record and no frame outcome. No sealed comparator file listed in `EV/RESTRICTED-FILES.md` was opened.
- **Research lanes.** Five Subfleet research lanes were briefed (`~/reviews/microcosm-start-plan-20261004/briefs/`) and cancelled before they started, when every Codex lane was on hold; the drafter did that reading itself. The independent review of this draft is recorded on the pull request that adds it.
- **No forecast** is registered here. Each candidate's registration carries its own.

### What comes next

1. Floors for H1's two arms and gate 3, and A1's floors, built from real data only, with the partitions and bite checks.
2. Two referee rounds independent of the drafter.
3. Max's ratification of K, k and gate 3's constants, then the lock in `gates.yaml`.
4. One registration comment per candidate, each frozen before its run.
