# Starting the projections from Microcosm's US population

**Status:** proposal, 4 October 2026. Nothing in it has run. The tests it proposes are drafted as an issue #42 registration in [`microcosm-start-registration-draft.md`](microcosm-start-registration-draft.md). That draft is not posted; posting it waits for Max's go. [Decisions needed](#decisions-needed) lists the calls.

**In one line:** the projections should start from the people in Microcosm's US population, the one PolicyEngine's model already runs on, with each person's past earnings matched from PSID donors and their income and wealth taken from Microcosm. Four new tests, registered before any code exists, would decide whether each piece is fit to use.

## In brief

Microcosm Dynamics aims to follow a representative population of Americans through work, family and retirement, apply Social Security's rules to each person, and carry each reform through the taxes and benefits a household faces at each level of government. Today the two projection tests follow a sample from the Panel Study of Income Dynamics (PSID): 11,405 people in 7,142 families from its 2011 interview, aged from 2010 to 2030 (`runs/replication_urban2010_cola_v1.json`, `cohorts.2011`). This plan starts the projections instead from Microcosm's US population, the cross-section of households that PolicyEngine-US already runs on.

- **Why start from Microcosm.** Microcosm's frame is the population PolicyEngine-US computes taxes and benefits for, so a projection that starts there can go through PolicyEngine-US without a second population. Its weights are calibrated to administrative totals, including Social Security payments by benefit type and household net worth (issue #42, Registration 19). It carries non-wage income and wealth that the PSID either lacks or measures with a small sample. The paper already describes the model as "built to project from Microcosm's frame in place of a PSID sample" and notes that no projection does so yet (`paper/paper.qmd:362`).
- **The hard part is the past.** A cross-section records one year of a person's earnings. A Social Security benefit depends on up to 35 years of them. Each person in the frame therefore needs an earnings history before the benefit rules can run.
- **How each person gets a history.** We match each person to people in the PSID who looked like them in the start year (same age, sex and earnings rank), and build the history backward one step at a time from those donors. This is the method that passed gate 1, the earnings-history test (`runs/gate1_rank_knn_v5.json`). A quantile regression forest (QRF) that predicts each year from the next one failed that test because it forgets a person's history: the correlation of log earnings ten years apart came out at 0.31 to 0.37, against 0.54 in the held-out PSID records and a pass band of ±0.07 (`runs/gate1_qrf_baseline_v1.json`). QRF versions given a fixed effect for each person went the other way, at 0.62 to 0.67, and failed too. A second candidate adds marital status to the match, and education once the frame carries it, and a QRF that uses every predictor the frame offers runs as a registered comparison. Years the PSID cannot supply, such as before 1968 and the odd years after 1996, come from fills learned on SSA's earnings file once that test locks.
- **Income and wealth.** They come from Microcosm, not the PSID. In the first version each component grows with the projection's assumptions, and each person keeps their rank within their age group as they age. A report-only check against the PSID's wealth panels measures how well that works. The two projection tests that exist today use no non-wage income or wealth at all. Only the static 13 percent cut test does, and the illustrative households set theirs by hand.
- **New tests.** A *gate*, in this repository, is a test we register publicly before running it; a part of the model counts as tested only after it passes. This plan proposes four. H1 scores the earnings histories against careers no candidate has seen, in SSA's records and in the PSID. W2 checks the starting population against SSA's published counts and average benefits. Gate 3, which `gates.yaml` names but has never given cells, would score the projection's first year against SSA's next published figures. A1 reports how well income and wealth age. The draft registration fixes their held-out data, cells and pass rules before anything is built.
- **What comes first.** Two pieces of open work feed this one: the fills learned on SSA's earnings file (gate_epuf_fill, awaiting Max's ruling d927 and pull requests #515 and #516), and forward earnings in the projections (Track B, awaiting d765, d781 and d782). The history work can start now and does not wait on either.
- **The schedule.** The draft 24-month plan shown at NASI builds the projected population through PolicyEngine in months 5 to 9 on the current PSID projections, and leaves running the dynamics on Microcosm's frame outside the 24 months. This plan proposes a lighter path that runs the existing engine on frame persons without the kernel changes Microcosm's design names, so the months 5 to 9 population can start from Microcosm. It needs about 70 to 105 agent-days of build work and 21 to 29 days of human review (assumptions, section 4.2), and the history work can be done before funding starts.
- **Risks.** The frame's weights are concentrated: the 166,302 people in the frame gate w1 pins carry an effective sample size of about 14,300 (`gates.yaml:4345`), while a dense Microcosm build has about 180,000. The frame has no education variable. Its older beneficiaries are 85.6 percent married, against about 60 percent in a published MINT tabulation (Registration 19). A 2024 frame cannot start the 2010 projections that the DYNASIM3 comparisons use. PolicyEngine-US takes Social Security benefits as inputs, so the benefit rules stay in the dynamics engine.

## Where things stand

### What the projection tests use today

Exercises 1 and 3 (a one-point COLA cut and a full retirement age of 68) project a closed PSID cohort from 2010 to 2030 under the 2008 Trustees Report's intermediate assumptions (`paper/paper.qmd:140`; `cola_track_a/config.py:264-268`). The cohort is everyone in the 2011 PSID wave born in 1980 or earlier, weighted by the 2011 wave's weight (`cola_track_a/config.py:128-167`). The engine runs mortality, aging, widowhood when a linked spouse dies, disability-insurance entitlement and claiming each year. It draws no marriages, divorces, births or earnings (`cola_track_a/adapters.py:1-36`). Benefits come from 1968–2010 careers, and the 2,190 people already receiving benefits in 2010 keep the benefit basis fixed at that year (`cola_track_a/config.py:245-247`; `runs/replication_urban2010_cola_v1.json`, `cohorts.2011.opening_stock_by_component`).

They use no non-wage income or wealth (section 2.1).

### What Microcosm's US population carries

Microcosm builds the US population from manifest-defined source stages (Microcosm `packages/microcosm-build/src/microcosm/build/us/source_stages.json`, at `main` `48fa06166`). The ones that matter here:

- **CPS ASEC** person records supply age, sex, marital status, earnings, reported benefits and retirement-account withdrawals (stage `retirement_distributions`, line 2139). The frame Registration 19 pins pools the 2022, 2023 and 2024 supplements (its `source_year` column).
- **IRS Public Use File, tax year 2015, uprated** (stage `puf_tax_detail`, line 7) supplies tax detail on a separate support channel of cloned records: earnings, interest, dividends, capital gains, pensions, IRA withdrawals, rents and business income, and the four Social Security components.
- **SCF 2022 and SIPP 2023** (stage `scf_wealth`, line 857) supply household net worth, through a QRF anchored on the SCF's net worth, and bank, stock and bond holdings, through a 50/50 blend of SIPP and SCF donors that places each household's holdings on its reference person. The SCF's components (home value, retirement accounts, business equity) are used in construction and not exported.
- **A CPS panel link** (stage `prior_year_income`, line 1800) joins adjacent supplements to recover the previous year's earnings for matched records and imputes it to the PUF channel. The release keeps the self-employment part and an availability flag, but drops prior-year wages.

Calibration sets household weights to administrative totals, among them IRS income statistics, Social Security payments by benefit type and Census population counts by age (`paper/paper.qmd:362`), SSI dollars and recipients, and household net worth (Registration 19). It does not target beneficiary counts, liquid assets or marital composition (Registration 19).

Microcosm extends the 2024 population to later years by **static aging**: one file per year to 2035, each reweighted from the original frame to SSA's population by age and sex, with monetary inputs scaled to projected aggregates and every record, age and ID kept (Microcosm `docs/us-annual-static-aging.md:1-40`; `DESIGN.md:161-180`, "Annual cross-sectional projections"). Static aging produces cross-sections, not trajectories. Nobody in it ages, marries, claims or dies.

### What the 24-month plan says

The draft 24-month plan Max showed as a backup slide at NASI on 1 October comes from a PlanGraph plan (`~/nasi-2026-slides/app/slides/MilestonesSlide.tsx`; `~/microcosm-launch-evidence/nasi-meeting-20261001/plangraph/dynamics-phase2.yaml`). Month 0 is the start of funding, January 2027 in the plan's calendar. Forward earnings in the projections run in months 2 to 5 and sit on the critical path. A registered real-PSID population run through PolicyEngine (d727) runs in months 2 to 4. "Projected population through PolicyEngine: federal, state, local" runs in months 5 to 9.

Two details matter here. First, the PlanGraph item behind months 5 to 9 is labeled "built on the current projections", which start from the PSID (`dynamics-phase2.yaml`, item `pop-pipeline`). Second, a separate item, "Run the dynamics as an operator on Microcosm's frame (person-period keys, entry and exit, household weight shares)", has six months of work and does not fit inside the 24 months; the leveling report says so (`dynamics-phase2.report.txt`, warning on `microcosm-port`). The speaker notes put it as "a further six months, or a third person". This plan separates two things that item bundles together:

- **Starting from Microcosm's people** (this plan): give frame persons histories and starting states, and run the existing microcosm-dynamics engine on them. No change to Microcosm's kernel.
- **Moving the engine into Microcosm** (the `microcosm-port` item): the kernel changes Microcosm's design names for longitudinal work, namely person-period keys, entry and exit markers, and a weight-share operator for households that recompose (Microcosm `DESIGN.md:182-215`, "Longitudinal (the social-security-model direction)"). That remains later work.

The first can be ready for months 5 to 9; the second need not be.

## 1. Earnings histories

### 1.1 Who needs one, and for what

| Group in the start year | What the projection needs from the past | Source in this plan |
|---|---|---|
| Not yet entitled, ages 22–61 | Covered earnings for every year from age 22 (earlier where they count), to compute insured status and AIME at entitlement | A generated history (section 1.4) |
| Not yet entitled, 62 and older | The same, plus earnings that the retirement earnings test would count | A generated history; forward earnings from Track B |
| Already receiving a retired-worker or disabled-worker benefit | The benefit in payment and the PIA behind it, for COLAs, conversions, recomputation, and spouse and survivor benefits | The frame's benefit, with the PIA inferred from it (section 1.6); a history only for grouping by lifetime earnings |
| Receiving a spouse's, widow(er)'s or child's benefit | The linked worker's PIA | The frame's benefit and spouse link; for widow(er)s, the deceased worker's PIA inferred from the survivor benefit |
| Children and people not yet working | Nothing from the past | Forward earnings (Track B) and, later, births and immigrants |

The table is the design's first decision: people already receiving benefits keep the benefit the frame reports, and the history machinery serves mainly people who have not yet claimed. The PSID projection handles its opening stock differently. It takes who receives which benefit from the PSID's reports, computes the amount from the person's recorded career, and fixes that basis at the opening year (`cola_track_a/opening.py:1-60`; `cola_track_a/config.py:245-247`, ruling d075). A frame start has no recorded careers to compute from, only generated ones, so it keeps the reported amount and infers the PIA from it (section 1.6). The alternative, computing every opening benefit from a generated history, would be internally consistent but would discard the one benefit fact the frame observes. W2 reports both.

### 1.2 What the cross-section observes, and what donors carry

A history can only be matched on what the frame observes in the start year. Registration 19's frame (`populace-us-2024-spm-20260909`) carries, by its column list:

- **age** (`age`): single years to 79, with 80 standing for 80–84 and 85 for 85 and over;
- **sex** (`is_female`; the CPS's `A_SEX`);
- **marital status and spouse** (the CPS's seven-way `A_MARITL`, `is_separated`, `is_surviving_spouse`; the spouse's line `A_SPOUSE` and the marital unit `person_marital_unit_id`);
- **earnings** (`employment_income_before_lsr`, `self_employment_income_before_lsr`, `self_employment_income_last_year`; `weeks_worked`, `hours_worked_last_week`);
- **Social Security** by type (`social_security_retirement`, `_disability`, `_survivors`, `_dependents`) and the CPS's reasons for receipt (`RESNSS1`, `RESNSS2`);
- **disability** (`is_disabled` and the CPS's `PEDIS*` items);
- **year of entry to the US** (`PEINUSYR`), nativity and citizenship;
- **class of worker and occupation** (`PEIO1COW`, `detailed_occupation_recode`);
- **provenance**: `source_year` and `person_support_channel`.

It carries **no educational attainment**. Neither does the frame gate w1 pins, nor a dense build from 8 July (section 5.4). It also drops the previous year's wages, which Microcosm's CPS panel link recovers for matched records, and keeps only the previous year's self-employment income and a flag (stage `prior_year_income`). With prior-year wages, a history could anchor on two observed years instead of one.

The donors carry different things:

- **The PSID** records head and spouse labor income for 1968–2022, annually through 1996 and every other year after (`paper/paper.qmd:164`). It records sex, age, education and marital history. It is small (9,152 families in 2023; `paper/paper.qmd:342`), and about half of the career years of its 2011-wave cohort through 2010 are imputed or set to zero (`paper/paper.qmd:164`). Its earnings are total labor income, not the covered, capped earnings the benefit formula uses.
- **SSA's 2006 Earnings Public-Use File (EPUF)** records capped, covered earnings for every year from 1951 to 2006 for 4,384,254 people, a 1 percent sample of Social Security numbers, with sex and year of birth and nothing else (`docs/amendments/gate_epuf_registration_proposal.md`; `paper/paper.qmd:366`). Its concept is the AIME's own. It cannot be matched on education or marital status, and it ends in 2006.

### 1.3 Two ways to build a history

**Rank-based donors (rank-kNN).** Gate 1's passing candidate generates a career backward from one observed year. Each person's earnings are converted to a rank within their five-year age band and year. For each earlier period, the model finds the 25 donor records nearest the person on the next one or two ranks already generated and on the person's anchor rank, draws one of them with probability proportional to its weight, and takes that donor's earlier rank. Dollars come from the PSID's earnings distribution for that age band and year at that rank. A separate participation model handles years without earnings (`scripts/run_gate1_candidate7.py:1-90`; `runs/gate1_rank_knn_v5.json`, `model`). Candidate 11 adds a fixed blend of the anchor rank with an estimate of each person's permanent rank (weight 0.1) and a regime for people with no earnings in the anchor year (`runs/gate1_rank_knn_v5.json`, `model.change_1_fixed_donor_blend`, `model.change_2_zero_anchor_participation_regime`). It passes gate 1 under the gate's second amendment (`runs/gate1_rank_knn_v5.json`, `verdict.gate_1_pass`). Its ten-year autocorrelation of log earnings is 0.499 to 0.533 across the five seeds, against 0.539 in the held-out records (`per_seed[].battery_checks.autocorr_log_10yr`).

**A QRF with every observed predictor.** Gate 1's baseline is populace-fit's regime-gated QRF run backward one step at a time. It predicts earnings two years earlier from earnings now and age then (`scripts/run_gate1_baseline.py:1-45`). It fails every seed. Two-year autocorrelation is right (0.712 to 0.735 against 0.730), but four-year autocorrelation falls to 0.557–0.591 against 0.657, and ten-year to 0.309–0.368 against 0.539, with tolerances of 0.06 and 0.07 (`runs/gate1_qrf_baseline_v1.json`, `per_seed[].battery_checks`). A chain that sees only the step before it forgets a person's level: each step's error compounds, and the correlation decays. The gate's own record says the same of a one-period clone, which scores 0.207 at ten years (`gates.yaml:176-186`).

Adding the frame's other variables (sex, education, marital status) to the QRF would restore some memory, because those variables do not change from step to step, but only the part of a person's permanent level they explain. The record shows what richer QRFs do, and they miss in both directions:

| Gate-1 candidate | What it adds to the QRF chain | Ten-year autocorrelation, five seeds (reference 0.539, tolerance 0.07) | Result |
|---|---|---|---|
| 1, baseline | nothing: next-period earnings and age | 0.309–0.368 | fails every seed (`runs/gate1_qrf_baseline_v1.json`) |
| 2 | a drawn permanent effect for the person, conditioning every step | 0.615–0.668 | battery fails every seed (`runs/gate1_qrf_latent_perm_v1.json`) |
| 3 | candidate 2 with a permanent-plus-persistent decomposition | 0.632–0.666 | battery fails every seed (`runs/gate1_qrf_latent_perm_v2.json`) |
| 4 | a structural three-component generator | 0.344–0.367 | fails every seed (`runs/gate1_qrf_structural_v1.json`) |

A person-level variable that conditions every step ties each year to the same draw and overshoots; without one, the chain forgets. A QRF that conditions every step on anchor-year earnings, the comparison this plan registers, is closest to candidates 2 and 3. Four attempts to tune persistence inside a QRF chain have failed.

**Whole-career donor splicing.** Copying one donor's whole recorded career, matched at the anchor year, was candidate 5a, which the repository calls MINT-style splicing. Its ten-year autocorrelation ran 0.583–0.639, and it failed the distribution tests in all five seeds. Splicing segments of up to three periods from different donors (5a′) passed the battery in all five seeds and failed the distribution tests in all five (`runs/gate1_splice_v1.json`, `runs/gate1_splice_v2.json`).

### 1.4 The recommended design

Use rank-kNN as the primary method, and let the new test H1 decide between it, a version that matches on more variables, and the QRF.

Why rank-kNN first:

1. **It is the method that passed.** It is the only earnings-history candidate with a gate-1 pass on the record (`runs/gate1_rank_knn_v5.json`).
2. **It keeps a person's place.** AIME averages a worker's 35 best indexed years, so what matters is whether high earners stay high. Microcosm's own design says so: "Earnings histories must preserve rank persistence (AIME is a 35-year order statistic): rank/copula methods across years over single-year marginals" (Microcosm `DESIGN.md:209-210`).
3. **It moves between data sets in ranks.** The anchor is a rank in the frame's own earnings distribution, and earlier years take dollars from the donor data's distribution at the same rank. Differences in level between the CPS-based frame and the PSID do not leak into the history.
4. **It anchors on exactly what the frame has.** Gate 1 already scores it as a backcast from one observed year (`scripts/run_gate1_baseline.py:22-36`), which is the frame's situation.

What has to be added, each as a registered change:

- **Anchor bridge.** The frame's records come from the 2022, 2023 and 2024 CPS supplements (its `source_year` column), whose earnings refer to 2021, 2022 and 2023, all carried to 2024. The PSID's last income year is 2022. The anchor is each person's rank within the frame as it stands, applied in the PSID's 2022 cell; the convention is registered, and H1's PSID arm scores it.
- **Sex-specific earnings distributions.** Gate 1 fits one distribution per age band and year for both sexes. Gate w1's third candidate split the interior bands by sex and found no collateral damage (`models/transport_deployment_v3.py:34-43`). Histories for the frame do the same.
- **Ages and years outside gate 1's range.** Gate 1 scores ages 25 to 59 and income years 1998 to 2022 (`gates.yaml:50-58`). A frame person who is 70 in the start year has a career that began around 1976. Years 1968–1996 are annual in the PSID, and the generator must step one year at a time there. H1 scores the whole career, so it covers this extension.
- **Covered, capped earnings.** PSID labor income is converted to a share of each year's wage base and capped at 1, the step gate_epuf_fill already defines (`docs/amendments/gate_epuf_fill_registration_proposal.md`, section 3, on branch `epuf-career-fill-20261003`). Work outside Social Security coverage is a separate gap. The repository has a draft design that would classify each person-year's earnings as covered wages, covered self-employment, uncovered or unresolved (`docs/design/covered_earnings_correction.md`, draft revision 2, which authorizes no implementation). Until it lands, histories treat all labor income as covered up to the wage base, as the PSID projection does.

The second candidate, **rank-kNN with covariates**, keeps donors to the person's sex and adds marital status to the distance; education joins by amendment once the frame carries it (section 5.4). Its weights are fixed in its registration before it runs. It answers the question the QRF is meant to answer (does matching on more of what the frame observes help?) without giving up the memory that made rank-kNN pass. The **QRF with every predictor** runs once as a registered comparison, so the answer to "why not a QRF?" rests on a scored run on the same held-out data.

### 1.5 Years the PSID cannot supply

The career assembler fills two kinds of gap with fixed rules: each odd year after 1996 is the mean of its neighbors, and nothing counts before 1968 or before age 22, whichever is later (`docs/amendments/gate_epuf_fill_registration_proposal.md`, "What this gate is, in plain words"). Max approved replacing both with fills learned on EPUF, because "we're overstating that form of persistence with our current method" (same document). Gate_epuf_fill scores those fills on EPUF people no fill has seen. Its tolerance awaits Max's ruling (d927), and pull request #516 adds the candidates.

Frame histories use whichever fills gate_epuf_fill certifies. If none is certified when H1 runs, they use the current rules and carry that label. For people born before 1946, whose careers began before 1968, the pre-1968 fill carries much of the career; H1 reports its cells by birth cohort so that shows.

### 1.6 People already receiving benefits

For a retired worker in the frame, the benefit in payment equals the PIA, reduced or increased for the claim age, with every COLA since entitlement. The frame does not record the claim age. We infer it the way the engine already assigns claim ages: from SSA's distribution of retired-worker awards by sex and year of entitlement (`paper/paper.qmd:151`). Dividing the benefit by the matching adjustment and COLA factors gives the PIA. Disabled workers need no claim-age adjustment. A widow(er)'s benefit gives the deceased worker's PIA the same way.

This inversion is only as good as the frame's benefit amounts. Registration 19 found that 16.9 percent of the frame's beneficiaries, by weight, carry a fixed-proportion split across all four Social Security components, synthetic from Microcosm's PUF-support channel. For them the split between retirement, survivor and disability benefits is not observed. W2 checks the inferred PIAs against SSA's published average PIA by age and sex for retired workers (Annual Statistical Supplement, Table 5.B1).

When a beneficiary needs a history for grouping (lifetime earnings quintiles, as MINT reports), it is generated with the inferred PIA's rank as the anchor in place of current earnings. Those histories do not change the beneficiary's benefit.

### 1.7 Couples

Spouse and survivor benefits depend on both spouses' records, and the spouses' careers are correlated. Histories built one person at a time keep only the correlation that runs through the two spouses' start-year ranks. Gate 2c scores marital status jointly with earnings on PSID couples (`runs/gate2c_hazard_v2.json`). H1's PSID arm adds two couple cells: the rank correlation of spouses' career earnings, and the share of couples in which the lower earner's career earnings are below half the higher earner's. That share is where spousal benefits and dual entitlement bite. If the cells fail, the next candidate draws couples' histories jointly from PSID couples.

### 1.8 Earnings after the start year

Track B owns forward earnings, and this plan does not duplicate it. The forward law is a rank chain fitted on PSID earnings through 2014 at ages 25 to 64. It converts ranks to dollars with an average-wage-index trend it fits on 2005–2014, and it has no fitted distribution above 64 (`paper/paper.qmd:168`). It passes gate m6 in 4 of 5 seeds (`runs/gate_m6_candidate3_v1.json`).

A Microcosm start asks three things of Track B, which its design should take as requirements:

1. **A start state from a frame person.** The law materializes each person's starting state at its boundary year, 2014: realized earnings in 2014 and 2012 and a permanent-rank estimate, and it refuses anyone without them (`engine/forward_earnings.py:1411-1435`). The engine gives fixed zero earnings to people outside that support (`engine/earnings_domain.py:1-7`). A frame person has the start year's earnings and a generated history, from which the same three pieces can be computed at the frame's start year. The law draws with the same machinery as the backward generator (25 neighbors, weights 1, 0.5 and 0.25, the fixed 0.1 blend; `engine/forward_earnings.py:64-77`), so the state the history ends in is the state the law starts from. Track B needs to accept a boundary year other than 2014.
2. **The projection's own wage index.** From a 2024 start, ranks should convert to dollars with the selected baseline's average wage index (the 2026 Trustees Report or CBO's 2026 projections, which pull request #512 makes selectable), not a trend fitted on 2005–2014.
3. **Ages 62 to 69.** The earnings test needs earnings at those ages, beyond the law's fitted range. The paper already plans a second law fitted on ages 25 to 69 (`paper/paper.qmd:382`).

Until Track B delivers, a Microcosm start can run only as an engineering run on invented data. Any real-data run without forward earnings would carry Track A's label ("no earnings after the start year"), and it would understate the AIME of people who claim in the following years.

## 2. Non-wage income and wealth

### 2.1 What the PSID supplies today

Only one of the four tests against DYNASIM3 reads non-wage income or wealth, and it is not a projection. Exercise 2, the 13 percent cut, counts the PSID's reported family money income and turns the family's PSID wealth into an annual income stream priced on NCHS 2000 life tables (`uniform_cut_track_u/runner.py:100-150, 216-218`; `cohorts/age67.py:86-98`). Exercises 1 and 3 report mean Social Security benefits by age; their code paths read no wealth, pension, interest, dividend or asset variable (a search of `cola_track_a/`, `fra68_track/`, `track_a_v2/`, `cohorts/psid2010.py` and `engine/` finds none). The illustrative households set pensions and savings by hand.

So nothing in the projections uses non-wage income or wealth yet. It starts to matter when the projected population goes through PolicyEngine-US, where it decides income taxes on benefits, SSI eligibility, SNAP and Medicaid, and poverty.

### 2.2 The Microcosm variables that replace it

The frame Registration 19 pins (`populace-us-2024-spm-20260909`) carries the following, read from its column list, with the stage that produces each from section "What Microcosm's US population carries".

| Income or wealth item (exercise 2's PSID concept) | Microcosm frame variables | Where Microcosm gets it |
|---|---|---|
| Earnings | `employment_income_before_lsr`, `self_employment_income_before_lsr` | CPS reports on CPS records (`WSAL_VAL`, `SEMP_VAL` carried raw); the 2015 PUF on the PUF channel. The anchor for histories |
| Social Security | `social_security_retirement`, `_disability`, `_survivors`, `_dependents` | CPS reports on CPS records (`SS_VAL` and the reasons `RESNSS1`, `RESNSS2` carried raw); the PUF on the PUF channel, where 16.9 percent of beneficiaries by weight carry a fixed-proportion split across all four (Registration 19, named difference 5). Calibrated to SSA dollars by type. After the start year the engine's computed benefits replace them |
| SSI | computed by PolicyEngine-US; `takes_up_ssi_if_eligible` | Take-up from CPS reports and SSA counts (stage `ssi_take_up`); the CPS report `SSI_VAL` is also carried |
| Defined-benefit pensions and annuities | `taxable_private_pension_income`, `tax_exempt_private_pension_income` | The PUF on the PUF channel (stage `puf_tax_detail`); on CPS records the frame also carries the CPS reports (`PNSN_VAL`, `ANN_VAL`) |
| Retirement-account withdrawals | `taxable_ira_distributions`, `tax_exempt_ira_distributions`, `taxable_401k_distributions`, `taxable_403b_distributions`, `taxable_sep_distributions`, `keogh_distributions` | CPS records, imputed by QRF onto the PUF channel (stage `retirement_distributions`) |
| Asset income | `taxable_interest_income`, `tax_exempt_interest_income`, `qualified_dividend_income`, `non_qualified_dividend_income`, `rental_income`, `s_corp_income`, `partnership_income`, `estate_income`, capital-gains variables | The PUF (stage `puf_tax_detail`) |
| Veterans' pensions, unemployment, workers' compensation | `veterans_benefits`, `unemployment_compensation`, `workers_compensation` | CPS reports, carried raw beside them (`VET_VAL`, `UC_VAL`, `WC_VAL`); workers' compensation from stage `workers_compensation_input` |
| Child support, alimony, other | `child_support_received`, `alimony_income`, `miscellaneous_income` | Child support from the CPS (stage `child_support_inputs`); alimony and other income from the PUF |
| Family wealth (PSID `WEALTH1`) | household `net_worth` | A QRF anchored on the SCF 2022's net worth (stage `scf_wealth`) |
| Liquid assets | `bank_account_assets`, `stock_assets`, `bond_assets` | A 50/50 blend of SIPP 2023 and SCF donors, placed on the household's reference person (stage `scf_wealth`) |
| Vehicles and auto loans | `household_vehicles_value`, `auto_loan_balance` | SIPP 2023 (stage `vehicle_assets`); SCF |
| Employer DC balances (exercise 2's row U7), home value | none | The SCF components are used in construction and not exported. A gap for any wealth result that needs them |

The W1-pinned sparse frame has no bank, stock or bond columns (Registration 19; confirmed in its column list), so the start uses a release that has them.

### 2.3 How they age forward

Nothing in the model projects wealth forward today. The first version keeps the rule simple enough to test:

1. **Growth.** Each dollar amount grows each year by the factor the selected baseline implies for it: wages for earnings-like items, prices for pensions with COLAs, and PolicyEngine-US's own uprating series elsewhere, so that a projected population and Microcosm's static aging agree on aggregates where they should (Microcosm `docs/us-annual-static-aging.md`).
2. **Life-cycle position.** Each person keeps a fixed rank within their sex and five-year age band for each item. As they age into the next band, the item takes the value at that rank in the next band's distribution in the start-year frame, grown as in step 1. A person whose rank sits inside a band's zeros has none of that item; pensions begin as the person ages into bands where fewer people have none. This uses the cross-section's age profile as each cohort's future, which overstates defined-benefit pensions for younger cohorts.
3. **Events.** When a spouse dies, the survivor keeps the household's assets. When a single person dies, their assets leave the population. From the start year on, Social Security income is the engine's computed benefit, and SSI, SNAP, Medicaid and taxes come from PolicyEngine-US each year.

The check A1 (section 3) applies the same rule to the PSID's wealth and income panels and reports how far it misses. It is report-only until its floors show it can tell a good rule from a bad one, the path gate_epuf took (`docs/amendments/gate_epuf_registration_proposal.md`).

### 2.4 What this does not do

It models no saving or spending decisions, no asset spend-down to qualify for SSI or Medicaid, no inheritance between generations and no response of retirement accounts to markets. A projection that reports results by wealth or by asset tests carries that label.

## 3. Tests

### 3.1 What existing gates cover

| Part of a Microcosm start | Test today | What it leaves open |
|---|---|---|
| Earnings dynamics learned from the PSID | gate 1 passes (`runs/gate1_rank_knn_v5.json`) | Scores 1998–2022 and ages 25–59, pooled over sex, on PSID people's own anchors (`gates.yaml:50-58`); never on frame people or full careers |
| Filling years the PSID did not record | gate_epuf_fill, registered and unlocked (pull requests #515, #516; d927) | Certifies fills on EPUF's concept, not the PSID-to-SSA gap |
| PSID earnings against SSA records | gate_epuf, report-only (#509) | Gates nothing |
| PSID processes carried onto the frame | gate w1 passes (`runs/gate_w1_candidate4_v1.json`) | Scores cross-sectional joints; certifies no transition and no history (`paper/paper.qmd:362`) |
| Forward earnings | gate m6 passes 4 of 5 seeds (`runs/gate_m6_candidate3_v1.json`); Track B's B2 awaits d765, d781, d782 | Fitted through 2014, ages 25–64 |
| Marriage, households, marriage by earnings | gates 2, 2b, 2c pass, 4 of 5 seeds each | Not yet inside a projection |
| Disability | gate m4 passes 5 of 5 seeds; SSDI entitlement not gated | |
| Mortality, claiming | not gated | |
| Benefit rules | the Python oracle; Axiom matches its AIME for 7,486 of 7,486 people (`paper/paper.qmd:182`) | |
| **Histories for frame people** | none | New test H1 |
| **The starting stock of beneficiaries and their inferred PIAs** | none | New test W2 |
| **The projection's first years from the frame** | none; `gates.yaml` names gate 3 for near-term outputs but gives it no cells (`paper/paper.qmd:202`) | Cells for gate 3 |
| **Income and wealth aging** | none | New check A1, report-only |
| **Projected population through PolicyEngine-US** | Registration 19's report-only design | Registered per analysis, as Registration 19 was |

### 3.2 New tests

Each test below is drafted in full, with its held-out data, cells and pass rules, in the [draft registration](microcosm-start-registration-draft.md). In short:

- **H1, earnings histories for a cross-section (gated).** Can a method, given only what the frame observes in one year, produce careers that look like real ones? It has two arms. The SSA arm hides every year of EPUF careers except 2006, asks each method to rebuild them from 2006 earnings, sex and birth year, and scores the rebuilt careers on people none of the methods learned from, using the split gate_epuf_fill already fixed. Its cells are what the benefit formula reads: the distribution of top-35-year indexed earnings, the share of years with no earnings, the share at the taxable maximum, the correlation between the anchor year and the career, and the ten-year autocorrelation, by sex and birth cohort. The PSID arm does the same on PSID families held out with seeds gate 1 never used, from 2022 earnings, age, sex and marital status, and adds the couple cells of section 1.7. Cells by education are reported, not gated, and show what leaving education out costs until the frame carries it. In the SSA arm, each cell's tolerance is the sampling error the frame itself carries there, so a method passes only if its error is no larger than what the frame's own sample would introduce. In the PSID arm, tolerances come from pairs of real held-out-size samples, the way gate 1 prices its battery.
- **W2, the starting population against SSA's records (report-only in its first run).** Do the frame's beneficiaries, with their inferred PIAs, match SSA's December counts and averages for the start year by type, age and sex (Annual Statistical Supplement tables 5.B1, 5.D1 and 5.G1, whose layout the repository has captured for the 2023 edition)? Microcosm calibrates Social Security dollars by type but not beneficiary counts (Registration 19), so counts and average PIAs are held out.
- **Gate 3, the first projected years (gated).** Project the frame one year forward and score the same cells against SSA's next December figures. The cell statistic is the drift: how much the projection's error grows over the frame's own starting error. This scores what the projection engine adds, not what the frame brings.
- **A1, income and wealth aging (report-only).** Apply section 2.3's rule to PSID families' wealth and income at one wave and compare with what the PSID recorded four years later, by age band.

### 3.3 How the tests get fixed before anything runs

The registration fixes each test's question, held-out data, split, cells, statistics, tolerance rule and pass rule. The tolerance multipliers it proposes are drafts until Max ratifies them at lock, as he is ruling on gate_epuf_fill's (d927). After posting:

1. Floors come from real data only: two disjoint halves of real careers in each cell, at the frame's effective sample size. No candidate is scored.
2. Bite: a method known to be wrong (gate 1's failed two-predictor QRF) must fail H1, and the real careers of one half must pass it with high probability. Cells that cannot meet both are report-only. A test with no bite does not lock.
3. Referee rounds, independent of the drafter, then Max's ratification, then the block enters `gates.yaml` locked.
4. Each candidate gets its own registration comment, frozen before its one scored run, as gate 1's candidates did on issue #42.

## 4. Order of work

### 4.1 What has to land first

- **gate_epuf_fill.** Max's ruling on its tolerance (d927), then its lock, then pull request #516's candidates and the one reading of its test data. Frame histories use the fills it certifies (section 1.5). H1's SSA arm reuses its split, so H1's floors can be built before it locks, but H1 is not scored until it does.
- **Track B.** Max's rulings on d765, d781 and d782, then B2's registration, then forward earnings in the projections, months 2 to 5 of the 24-month plan. Section 1.8 lists what a Microcosm start needs from it. The history work (tasks T1 to T6 below) does not wait for Track B; any projection from the frame does.
- **Pull request #512**, which makes the 2026 Trustees Report and CBO's 2026 projections selectable as the projection's baseline. A 2024 start needs one of them; the 2008 Trustees path the DYNASIM3 tests use stops at 2030 and predates every year the frame describes (Registration 18).
- **Four requests to Microcosm** (sections 5.1 and 5.4): restore educational attainment to the US release; keep the previous year's wages, which its CPS panel link already recovers for matched records, so a history can anchor on two observed years; explain the marital makeup of older beneficiaries; and publish a dense release for dynamics. None blocks the first candidate. The first blocks the second candidate's education term, and the last limits the precision of every cell.

### 4.2 Tasks

Effort is in agent-days of build work and days of human review. Every figure is an assumption, not a measurement.

| # | Task | Depends on | Agent-days | Review days |
|---|---|---|---:|---:|
| T1 | Pin the frame and write its reader: the person table of section 1.2, spouse links, source year, support channel and weights; tests on invented data | the frame choice (decision 2) | 3–5 | 1 |
| T2 | File the four Microcosm requests with evidence | — | 1–2 | 0–0.5 |
| T3 | H1's floors, bite checks and block draft; two referee rounds | the posted registration | 8–12 | 3–4 |
| T4 | H1's candidates and strawman, built on invented data | T3's interfaces | 8–12 | 2–3 |
| T5 | H1's lock and one scored run per candidate, each registered first | T3, T4, d927 | 3–5 | 2 |
| T6 | The starting stock: benefits as state, inferred PIAs, spouse and survivor links; W2's first run | T1 | 6–9 | 2 |
| T7 | Run the existing engine on frame people: starting states, fixed trajectory weights, the selected baseline | T1, T5, T6, #512 | 10–15 | 3–4 |
| T8 | Connect Track B's forward law from the frame's start state | T7, Track B | 4–6 | 1–2 |
| T9 | Income and wealth: the table of section 2.2, the aging rule, A1 | T1, T7 | 8–12 | 2–3 |
| T10 | Gate 3's cells, SSA captures for December of the start year and the next, and the scored run | T7, T8 | 5–8 | 2 |
| T11 | Each projected year through PolicyEngine-US, split by level of government | T7, T9; Registration 19's machinery | 8–12 | 2–3 |
| T12 | Differential checks: the oracle's AIME against PolicyEngine-US's `ss_aime` on the same histories; a PSID start against a Microcosm start in a common year; dynamic against static aging aggregates | T5, T7 | 5–8 | 1–2 |
| | **Total** | | **69–106** | **21–29** |

### 4.3 Where it sits in the 24-month plan

| When | Work | 24-month plan item it serves |
|---|---|---|
| October–December 2026, before funding | T1–T6 | none yet; this is the part that can start now |
| Months 0–5 | T7, T9, T12 | runs beside "forward earnings in the projections" (months 2–5) |
| Month 5 | T8 | as Track B lands |
| Months 5–9 | T10, T11 | "projected population through PolicyEngine: federal, state, local" (months 5–9), now starting from Microcosm |

This changes one assumption of the PlanGraph draft: its months 5 to 9 item is "built on the current projections", which start from the PSID. On this schedule the item starts from Microcosm instead, without the kernel port. The registered real-PSID population run (d727, months 2 to 4) is unchanged; it is a static analysis of PSID people and needs no projection.

## 5. Risks

### 5.1 Weights

- **Concentration.** The frame gate w1 pins has 166,302 people, but its weights give an effective sample size (Kish) of 14,328, with one household weighing 433,329 (`gates.yaml:4345`). Registration 19's frame has 166,321 people and an effective size of about 27,000 (computed for this plan from its household weights; structure only). A dense Microcosm build from 8 July 2026, before pruning, has 865,046 people and an effective size of about 180,000 (`populace-us-2024-buildh-dense-warmstart-b449eb7`; same computation). The sparse release is built for fast PolicyEngine-US runs. A projection that follows people into small groups (widowed men at 62–64, long disability spells) needs the dense one, or its cells will be noisier than the PSID's. Decision 2 asks which to use.
- **Clones.** In Registration 19's frame, 58 percent of the weight sits on records from the PUF-support channel (same computation), and 16.9 percent of beneficiaries by weight carry a synthetic fixed-proportion split across all four Social Security components (Registration 19, named difference 5). For them the benefit type is not observed, and the PIA inference of section 1.6 is weak. W2 reports its cells with and without them.
- **Marital makeup.** The frame's beneficiaries aged 62 and over are 85.6 percent married, against about 60 percent in a MINT tabulation for 2022 (Registration 19, named difference 6). Spouse and survivor benefits rest on this. No spouse or survivor result from a Microcosm start should be published until Microcosm explains or fixes it; the request in T2 asks.
- **Weights over time.** Microcosm's design gives each trajectory one weight and stacks later years' targets on it (Microcosm `DESIGN.md:125-128`). The first version holds each person's start-year weight fixed, as the PSID projection holds the 2011 weight. With no births or immigrants until those models enter the projections, the projected population closes. People 50 and older in 2030 were all alive and in the frame in 2024, apart from later immigrants, so 2030 results by age for older people are covered; younger groups are not. PolicyEngine-US's own extension of the frame to later years grows weights with population and keeps ages fixed (Registration 19, "Year"); that is static aging, and a dynamic projection must not apply it on top.
- **Version drift.** Registration 19's frame was weighted under PolicyEngine-US 1.764.6 and runs under 2.18.0 (named difference 7). Each run records both.

### 5.2 A 2024 population against a 2010 test start

Exercises 1 and 3 start in 2010 because DYNASIM3's published reforms do. Microcosm's frame describes 2024, pooled from the 2022 to 2024 CPS supplements (the frame's `source_year` column). There are four ways to handle this:

- **A. Leave the DYNASIM3 tests on the PSID start (recommended).** Their one-shot runs are spent and public, so a Microcosm-start rerun would be post hoc in any case. The Microcosm start serves the comparisons that start in the 2020s: OACT's, PWBM's, MINT's and CBO's tables on the 2026 basis, which the 24-month plan schedules for months 12 to 15, and gate 3's near-term cells.
- **B. Compare the two starts in a common modern year.** Project both a PSID start from its 2023 wave and the Microcosm start from 2024 to 2030 under the same baseline, and report where they differ (T12). It isolates what the starting population does, on a horizon both can reach.
- **C. Build a 2010 Microcosm frame** from the 2011 CPS supplement and contemporaneous IRS and SCF files. It would allow a like-for-like rerun of exercises 1 and 3. Microcosm's US stages pin the 2022–2024 CPS supplements, the 2015 PUF, the 2022 SCF and the 2023 SIPP (`source_stages.json`), so a 2010 vintage needs new pins and inputs for every stage. It is months of Microcosm work for a post hoc result.
- **D. Wind the 2024 frame back to 2010.** Rejected: the people who died between 2010 and 2024 are missing, immigrants who arrived after 2010 are present, and cohort-specific rules (the FRA schedule by birth year) would apply to the wrong cohorts.

### 5.3 Benefit rules in PolicyEngine-US

PolicyEngine-US 2.24.1 (upstream `main` `a39cfa7136`) splits Social Security into what it computes and what it takes as given:

| Rule | PolicyEngine-US | The dynamics oracle |
|---|---|---|
| Benefits by type (retirement, disability, survivors, dependents) | Inputs with no formula; `social_security` adds the four (`variables/gov/ssa/ss/social_security.py`, `social_security_retirement.py`) | Computed |
| AIME and PIA from an earnings history | Computed in a separate path: `ss_aime` reads up to 45 prior years of `employment_income` and `total_self_employment_income`, capped at each year's wage base, or takes `ss_aime_input`; `ss_pia` applies the formula (`variables/gov/ssa/social_security/ss_aime.py`, `ss_pia.py`; `parameters/gov/simulation/aime_lookback_years.yaml`) | Computed (`cola_track_a/benefits.py`) |
| Claiming adjustment, earnings test | Computed in the same path (`ss_retirement_age_adjustment_factor.py`, `ss_earnings_test_reduction.py`, `ss_retirement_benefit_before_earnings_test.py`) | Adjustment computed; earnings test parameters held, not applied (`paper/paper.qmd:172`) |
| Spouse, survivor and child benefits, family maximum, dual entitlement | Not modeled | Spouse and survivor benefits computed in the projections; the family maximum and dual-entitlement reductions are in Track B's gross-benefit layer (`track_b/gross_benefits.py`), tested on SSA's worked examples (`tests/test_track_b_gross_benefits.py`), and not yet used by a projection |
| Taxation of benefits | Computed (`variables/gov/irs/income/taxable_income/adjusted_gross_income/irs_gross_income/social_security/`), with the revenue credited to OASDI and Medicare (`variables/gov/ssa/revenue/tob_revenue_*.py`) | Not modeled |
| SSI | Computed, with income deeming from an ineligible spouse or parent (`variables/gov/ssa/ssi/eligibility/income/deemed/`); no resource deeming (Registration 19, named difference 3) | A static offset in exercise 2 only |

No variable outside `variables/gov/ssa/social_security/` reads `ss_pia`, `ss_earnings_test_reduction` or `ss_retirement_benefit_before_earnings_test`, so PolicyEngine-US's own benefit path does not feed the components its other programs read.

The consequence for this plan: the dynamics engine computes the benefits and hands PolicyEngine-US the four components each year, as the illustrative households do now. PolicyEngine-US then computes taxes on benefits, SSI, SNAP, Medicaid and state programs. Its own AIME is a second implementation of the same rule, so T12 compares the two on the same histories. Registration 19 names two SSI gaps that matter for a projected population: no deeming of an ineligible spouse's resources, and a cap on deemed-income benefits that differs from the regulation (named differences 3 and 12).

### 5.4 Other risks

- **No education in the frame.** None of the Microcosm US releases checked for this plan carries educational attainment: not the W1 pin, not Registration 19's frame, not the dense build. Both source surveys record it (the CPS's `A_HGA`, the ACS's `SCHL`), and Microcosm already restores reviewed CPS person columns from the pinned Census files (Microcosm `docs/us-asec-census-person-columns.md`). Until it adds this one, the second candidate's education term and H1's education cells cannot run on the frame.
- **Three vintages in one frame.** Records come from the 2022, 2023 and 2024 CPS supplements, whose earnings refer to 2021, 2022 and 2023, uprated to 2024. The anchor rank is computed within the frame as it stands, and the registration states that convention.
- **Ages top-coded at 80 and 85.** The frame stores ages 80–84 as 80 and 85 and over as 85. Mortality, widowhood and survivor timing need single years; the starting age within each band is drawn from SSA's population by single year and registered.
- **Immigrants.** The frame carries year of entry (`PEINUSYR`). A history starts no earlier than the year of entry, so recent immigrants have short US careers, as SSA records them.
- **Uncovered work.** Some state and local government workers are outside Social Security. The frame carries class of worker (`PEIO1COW`); the PSID does not separate covered from uncovered work in most years. The repository's covered-earnings correction is a draft design, not code (`docs/design/covered_earnings_correction.md`). Until it lands, a current government worker's whole history counts as covered, which overstates benefits for workers outside the system.
- **People in institutions.** The CPS leaves out people in nursing homes and other institutions, many of them old beneficiaries. W2's counts by age show the gap.
- **Restricted data and compute.** The frame carries values imputed from the IRS Public Use File. Registration 19 runs it on Modal under a ruling specific to that analysis (d806); the general question for PUF-derived files is parked (d093). Each registration in this plan states where it runs, and runs stay local under `heavy` unless a ruling covers them.
- **Blinding.** None of these tests needs a sealed comparator. Any later blind test that needs a projected population waits until the projection gates pass (`paper/paper.qmd:396`), and its builders are briefed on `RESTRICTED-FILES.md`.

## Decisions needed

1. **Post the registration?** The go to post the draft registration on issue #42, after the independent review this plan's pull request records. It fixes H1, W2, gate 3's cells and A1 before any code. Queued as a decision; nothing is posted before Max's go.
2. **Which frame for dynamics?** The dense pool (effective size about 180,000 in July's build) or the sparse release PolicyEngine-US uses (about 27,000)? This plan recommends the dense pool for the projection and the sparse release only where a result must match a published PolicyEngine-US run. This is a methodology choice with more than one defensible answer.
3. **Tolerance multipliers.** H1 and gate 3's multipliers are drafts; Max ratifies them at lock, as for gate_epuf_fill (d927).
4. **The 2010 question.** Section 5.2 recommends option A plus B, and not C, for now.

## Sources

Code and artifacts are cited at microcosm-dynamics `master` `492d5a60f`, Microcosm `main` `48fa06166`, and PolicyEngine-US `main` `a39cfa7136` (2.24.1), with package paths under `src/populace_dynamics/` unless stated. Issue #42's Registration 19 is comment 5961843703. The 24-month plan is the NASI backup slide (`~/nasi-2026-slides/app/slides/MilestonesSlide.tsx`) and its PlanGraph source (`~/microcosm-launch-evidence/nasi-meeting-20261001/plangraph/`), both local to Max's machine. Frame structure (column lists, source years, support channels and effective sample sizes from household weights) was read from the cached Hugging Face files named above; no outcome was computed on any frame.
