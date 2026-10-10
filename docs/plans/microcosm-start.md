# Starting the projections from Microcosm's US population

**Status:** proposal, 4 October 2026, revised after two rounds of independent review. Nothing in it has run. The tests it proposes are drafted as an issue #42 registration in [`microcosm-start-registration-draft.md`](microcosm-start-registration-draft.md). That draft is not posted; posting it waits for Max's go (decision d947). [Decisions needed](#decisions-needed) lists the calls.

**In one line:** the projections should start from the people in Microcosm's US population, the one PolicyEngine's model already runs on, with each person's past earnings matched from PSID donors and their income and wealth taken from Microcosm. Two new gates and two report-only checks, registered before any code exists, would decide whether each piece is fit to use.

A **gate**, in this repository, is a pass-or-fail test whose rules we publish before running it; a part of the model counts as tested only after it passes. A **report-only check** is published the same way, with no pass or fail.

## In brief

Microcosm Dynamics aims to follow a representative population of Americans through work, family and retirement, apply Social Security's rules to each person, and carry each reform through the taxes and benefits a household faces at each level of government. Today the two projection tests follow a sample from the Panel Study of Income Dynamics (PSID): 11,405 people in 7,142 families from its 2011 interview, aged from 2010 to 2030 (`runs/replication_urban2010_cola_v1.json`, `cohorts.2011`). This plan starts the projections instead from Microcosm's US population, the cross-section of households that PolicyEngine-US already runs on.

- **Why start from Microcosm.** It is the population PolicyEngine-US computes taxes and benefits for, so a projection that starts there can go through PolicyEngine-US without a second population. Its weights are calibrated to administrative totals, including Social Security payments by benefit type and household net worth (issue #42, Registration 19). It carries non-wage income and wealth from the CPS, the IRS file, the SCF and the SIPP. The paper already describes the model as "built to project from Microcosm's frame in place of a PSID sample" and notes that no projection does so yet (`paper/paper.qmd:362`).
- **The hard part is the past.** A cross-section records one year of a person's earnings. A Social Security benefit depends on up to 35 years of them. Each person in the frame therefore needs an earnings history before the benefit rules can run.
- **How each person gets a history.** We match each person to people in the PSID who looked like them in the start year (same age, sex and earnings rank) and build the history backward one step at a time from those donors. This is the method that passed gate 1, the earnings-history gate (`runs/gate1_rank_knn_v5.json`).
  - A QRF (quantile regression forest) chain that predicts each year from the next failed gate 1 because it forgets a person's history. Its correlation of log earnings ten years apart came out at 0.31 to 0.37, against 0.54 in the held-out PSID records and a pass band of ±0.07 (`runs/gate1_qrf_baseline_v1.json`).
  - QRF versions given a fixed effect for each person went the other way, at 0.62 to 0.67, and failed too.
  - A second candidate adds marital status to the match. A QRF using the predictors H1 can align across the frame and the PSID runs once as a registered comparison.
  - Years the PSID cannot supply, such as before 1968 and the odd years after 1996, come from fills learned on SSA's earnings file once that gate locks.
- **Income and wealth.** They come from Microcosm, not the PSID. In the first version each item grows with the projection's assumptions, and each person or household keeps its rank within its age group as it ages. A report-only check against the PSID's wealth panels measures how well that works. The two projection tests that exist today use no non-wage income or wealth at all. Only the static 13 percent cut test does, and the illustrative households set theirs by hand.
- **New tests.**
  - **H1 (gate)** scores histories against careers no candidate has seen, in SSA's records and in the PSID.
  - **Gate 3** gets its first cells: the projection's first year against SSA's next published figures. `gates.yaml` names gate 3 but has never given it cells.
  - **W2 (report-only)** checks the starting population against SSA's published counts and averages.
  - **A1 (report-only)** reports how well income and wealth age.

  The draft registration fixes their held-out data, cells, pass rules, H1's three candidates and the rule for adopting one, all before anything is built.
- **What comes first.** Two pieces of open work feed this one:
  - the fills learned on SSA's earnings file (gate_epuf_fill, awaiting Max's ruling d927 and pull requests #515 and #516);
  - forward earnings in the projections (Track B, awaiting d765, d781 and d782).

  The history work can start now. H1's one scored run waits for gate_epuf_fill's verdict, and any real-data projection waits for Track B.
- **The schedule.** The draft 24-month plan shown at NASI builds the projected population through PolicyEngine in months 5 to 9, on the current PSID projections, after the earnings test and family maximum. It leaves running the dynamics on Microcosm's frame outside the 24 months. This plan proposes a lighter path: run the existing engine on frame persons, without the kernel changes Microcosm's design names, so the months 5 to 9 population can start from Microcosm. It needs about 70 to 109 agent-days of build work and 22 to 29.5 days of human review (assumptions, section 4.2).
- **Risks.**
  - **Concentrated weights.** The frame gate w1 pins holds 166,302 people with an effective sample size of about 14,300 (`gates.yaml:4345`). A dense Microcosm build has about 180,000, but it lacks the asset columns and the derived disability, self-employment, hours and weeks variables this plan needs.
  - **Missing education.** No release checked has an education variable.
  - **Marital makeup.** The frame's older beneficiaries are 85.6 percent married, against about 60 percent in a published MINT tabulation (Registration 19).
  - **Start year.** A 2024 frame cannot start the 2010 projections the DYNASIM3 comparisons use.
  - **Benefit rules.** PolicyEngine-US takes Social Security benefits as inputs, so the benefit rules stay in the dynamics engine.

## Where things stand

### What the projection tests use today

Exercises 1 and 3 (a one-point COLA cut and a full retirement age of 68) project a closed PSID cohort from 2010 to 2030 under the 2008 Trustees Report's intermediate assumptions (`paper/paper.qmd:235`; `cola_track_a/config.py:264-268`).

- **The cohort.** Everyone in the 2011 PSID wave born in 1980 or earlier, weighted by the 2011 wave's weight (`cola_track_a/config.py:127-167`).
- **Each year.** The engine runs mortality, aging, widowhood when a linked spouse dies, disability-insurance entitlement and claiming. It draws no marriages, divorces, births or earnings (`cola_track_a/adapters.py:1-36`).
- **Benefits.** People who were not yet receiving benefits in 2010 get benefits computed from their 1968–2010 careers. The 2,190 people already receiving benefits in 2010 keep the amount the PSID recorded for them, carried forward with COLAs (`cola_track_a/benefits.py:747-790`; `cola_track_a/config.py:245-247`, ruling d075; `runs/replication_urban2010_cola_v1.json`, `cohorts.2011.opening_stock_by_component`).

They use no non-wage income or wealth (section 2.1).

### What Microcosm's US population carries

Microcosm builds the US population from manifest-defined source stages (Microcosm `packages/microcosm-build/src/microcosm/build/us/source_stages.json`, at `main` `48fa06166`). The ones that matter here:

- **The CPS ASEC.** Person records supply age, sex, marital status, earnings and reported benefits; the frame carries the CPS's own columns (`A_AGE`, `A_MARITL`, `WSAL_VAL`, `SS_VAL` and others). The pool's `source_year` is the income year: Microcosm pins income years 2022, 2023 and 2024 to the 2023, 2024 and 2025 supplements (`us_runtime/asec_pool.py:54-61, 314`; `us_runtime/education_assistance_source.py:104-152`), and Registration 19's frame holds all three.
- **The IRS Public Use File, tax year 2015, uprated** (stage `puf_tax_detail`, line 7). It supplies tax detail on a separate support channel of cloned records: earnings, interest, dividends, capital gains, pensions, IRA withdrawals, rents and business income, and the four Social Security components.
- **The SCF 2022 and SIPP 2023** (stage `scf_wealth`, line 857). They supply:
  - household net worth, through a QRF anchored on the SCF's net worth;
  - bank, stock and bond holdings, placed on the household's head (`source_stages.json:1141-1150`).

  On current `main` the holdings come from a 50/50 blend of SIPP and SCF donors (`source_stages.json:1133-1138`). Registration 19 could not confirm the blend for the frame it pins. The SCF's components (home value, retirement accounts, business equity) are used in construction and not exported.
- **A CPS panel link** (stage `prior_year_income`, line 1800). It joins adjacent supplements to recover the previous year's earnings for matched records. Unmatched records fall back to the current year's value (`source_stages.json:1829-1832`), and PUF records get a QRF imputation. The release keeps the self-employment part and an availability flag (`previous_year_income_available`), but drops prior-year wages.

**Calibration.** Household weights are calibrated to administrative totals, among them IRS income statistics, Social Security payments by benefit type and Census population counts by age (`paper/paper.qmd:362`), SSI dollars and recipients, and household net worth (Registration 19). Calibration does not target beneficiary counts, liquid assets or marital composition (Registration 19).

**Static aging.** Microcosm extends the 2024 population to later years by static aging: one file per year to 2035, each reweighted from the original frame to SSA's population by age and sex, with monetary inputs scaled to projected aggregates and every record, age and ID kept (Microcosm `docs/us-annual-static-aging.md:1-40`; `DESIGN.md:161-180`, "Annual cross-sectional projections"). Static aging produces cross-sections, not trajectories. Nobody in it ages, marries, claims or dies.

### What the 24-month plan says

The draft 24-month plan Max showed as a backup slide at NASI on 1 October comes from a PlanGraph plan (`~/nasi-2026-slides/app/slides/MilestonesSlide.tsx`; `~/microcosm-launch-evidence/nasi-meeting-20261001/plangraph/dynamics-phase2.yaml`). The schedule:

- Month 0 is the start of funding, January 2027 in the plan's calendar.
- Forward earnings in the projections run in months 2 to 5, on the critical path.
- A registered real-PSID population run through PolicyEngine (d727) runs in months 2 to 4.
- "Projected population through PolicyEngine: federal, state, local" runs in months 5 to 9.

Three details matter here:

- **The months 5 to 9 item is built on the PSID.** Its PlanGraph item is labeled "built on the current projections", which start from the PSID (`dynamics-phase2.yaml`, item `pop-pipeline`).
- **It waits on two other items.** It depends on the real-PSID run and on the earnings test and family maximum in the projections (items `real-psid-run` and `ret-famax`, lines 150–152).
- **Running on Microcosm's frame does not fit.** A separate item, "Run the dynamics as an operator on Microcosm's frame (person-period keys, entry and exit, household weight shares)", has six months of work and does not fit inside the 24 months; the leveling report says so (`dynamics-phase2.report.txt`, warning on `microcosm-port`). The speaker notes put it as "a further six months, or a third person".

This plan separates two things that item bundles together:

- **Starting from Microcosm's people** (this plan): give frame persons histories and starting states, and run the existing microcosm-dynamics engine on them. No change to Microcosm's kernel.
- **Moving the engine into Microcosm** (the `microcosm-port` item): the kernel changes Microcosm's design names for longitudinal work, namely person-period keys, entry and exit markers, and a weight-share operator for households that recompose (Microcosm `DESIGN.md:182-215`, "Longitudinal (the social-security-model direction)"). That remains later work.

The first can be ready for months 5 to 9; the second need not be.

## 1. Earnings histories

### 1.1 Who needs one, and for what

| Group in the start year | What the projection needs from the past | Source in this plan |
|---|---|---|
| Not yet entitled, ages 22–61 | Covered earnings for every year from age 22 (earlier where they count), to compute insured status and AIME at entitlement | A generated history (section 1.4) |
| Not yet entitled, 62 and older | The same, plus the earnings the retirement earnings test would count | A generated history; forward earnings from Track B |
| Already receiving a retired-worker or disabled-worker benefit | The benefit in payment, and the PIA behind it for conversions, recomputation, and spouse and survivor benefits | The frame's benefit, with the PIA inferred from it (section 1.6); a history only for grouping by lifetime earnings |
| Receiving a spouse's, widow(er)'s or child's benefit | The linked worker's PIA | The frame's benefit, kept as state. The linked worker's PIA is not inferred in the first version (section 1.6); rules that need it are counted as unsupported for these people |
| Whose benefits depend on someone not in the frame: divorced spouses, and widow(er)s not yet entitled | The ex-spouse's or deceased spouse's record | None today. A named limit: these benefits are left out and the people are counted. A later candidate could generate a "virtual spouse" history matched on the survivor's characteristics |
| Children and people not yet working | Nothing from the past | Forward earnings (Track B) and, later, births and immigrants |

The table is the design's first decision: people already receiving benefits keep the benefit the frame reports, and the history machinery serves mainly people who have not yet claimed. The PSID projection does the same for its own opening stock. It carries each 2010 beneficiary's recorded amount forward with COLAs and never computes it from the career (`cola_track_a/benefits.py:747-790`, `opening_stock_amounts`; the opening-stock path at lines 832–834). The new part is the PIA. The PSID projection never needs one for its opening stock, because spouse and survivor links run through projected people whose careers are recorded. A frame start does need one, and infers it (section 1.6).

### 1.2 What the cross-section observes, and what donors carry

A history can only be matched on what the frame observes in the start year. Registration 19's frame (`populace-us-2024-spm-20260909`) carries, by its column list (`docs/plans/microcosm-start-evidence/frame_structure.txt`):

- **age** (`age`): single years to 79, with 80 standing for 80–84 and 85 for 85 and over;
- **sex** (`is_female`; the CPS's `A_SEX`);
- **marital status and spouse** (the CPS's seven-way `A_MARITL`, `is_separated`, `is_surviving_spouse`; the spouse's line `A_SPOUSE` and the marital unit `person_marital_unit_id`);
- **earnings** (`employment_income_before_lsr`, `self_employment_income_before_lsr`, `self_employment_income_last_year` with `previous_year_income_available`; `weeks_worked`, `hours_worked_last_week`; `is_self_employed`);
- **Social Security** by type (`social_security_retirement`, `_disability`, `_survivors`, `_dependents`) and the CPS's reasons for receipt (`RESNSS1`, `RESNSS2`);
- **disability** (`is_disabled` and the CPS's `PEDIS*` items);
- **year of entry to the US** (`PEINUSYR`), nativity and citizenship;
- **class of worker and occupation** (`PEIO1COW`, `detailed_occupation_recode`);
- **provenance**: `source_year` (the income year) and `person_support_channel`.

It carries **no educational attainment**, and neither does the frame gate w1 pins or the dense build from 8 July (section 5.4). It drops the previous year's wages; with them, a history could anchor on two observed years for matched CPS records.

The dense build lacks several of the columns above: `is_disabled`, `is_self_employed`, `is_separated`, `is_surviving_spouse`, `weeks_worked`, `hours_worked_last_week`, `self_employment_income_last_year`, `previous_year_income_available` and `detailed_occupation_recode` (same evidence file). Section 5.1 takes this up.

The donors carry different things:

- **The PSID** records head and spouse labor income for 1968–2022, annually through 1996 and every other year after (`paper/paper.qmd:164`). It records sex, age, education, marital history and work limitation. It is small (9,152 families in 2023; `paper/paper.qmd:342`), and about half of the career years of its 2011-wave cohort through 2010 are imputed or set to zero (`paper/paper.qmd:164`). Its earnings are total labor income, not the covered, capped earnings the benefit formula uses. The repository reads its work-limitation status (`data/disability.py`) but not its hours, self-employment or education yet.
- **SSA's 2006 Earnings Public-Use File (EPUF)** records capped, covered earnings for every year from 1951 to 2006 for 4,384,254 people, a 1 percent sample of Social Security numbers, with sex and year of birth and nothing else (`paper/paper.qmd:366`). Its concept is the AIME's own. It cannot be matched on anything but age, sex and earnings, and it ends in 2006.

### 1.3 Ways to build a history, and what gate 1 found

**Rank-based donors (rank-kNN).** Gate 1's passing method generates a career backward from one observed year:

1. Each person's earnings become a rank within their five-year age band and year.
2. For each earlier period, the method finds the 25 donor records nearest the person on the next one or two ranks already generated and on the person's anchor rank.
3. It draws one of them with probability proportional to its weight and takes that donor's earlier rank.
4. Dollars come from the PSID's earnings distribution for that age band and year at that rank.

A separate participation model handles years without earnings (`scripts/run_gate1_candidate7.py:1-90`; `runs/gate1_rank_knn_v5.json`, `model`). The record is in `runs/gate1_rank_knn_v5.json`, `changes` and `model`:

- **Lineage.** The zero-anchor regime came from candidate 9. Candidate 10 added a fixed blend of the anchor rank with an estimate of each person's permanent rank (weight 0.1). Candidate 11, the passing run, is byte-identical to candidate 10.
- **The pass rests on an amendment.** Candidate 10 failed. Candidate 11 passed under the gate's second amendment, which scores one classifier test by its mean over 20 seeds (`paper/paper.qmd:192`).

Its persistence by lag, over the five seeds (`per_seed[].battery_checks`), compared with the held-out records:

| Lag | Rank-kNN (candidate 11) | Held-out records | Tolerance | Result |
|---|---|---|---|---|
| 2 years | 0.762–0.790 | 0.730 | 0.05 | Too persistent; seed 0 fails, its one battery failure |
| 4 years | 0.683–0.703 | 0.657 | 0.06 | Passes |
| 10 years | 0.499–0.533 | 0.539 | 0.07 | Passes |

**QRF chains.** Gate 1's baseline is populace-fit's regime-gated QRF run backward one step at a time. It predicts earnings two years earlier from earnings now and age then (`scripts/run_gate1_baseline.py:1-45`). It fails every seed. Two-year autocorrelation is right (0.712 to 0.735, against 0.730), but four-year falls to 0.557–0.591 against 0.657, and ten-year to 0.309–0.368 against 0.539 (`runs/gate1_qrf_baseline_v1.json`, `per_seed[].battery_checks`). A chain that sees only the step before it forgets a person's level. The gate's record says the same of a one-period clone, which scores 0.207 at ten years (`gates.yaml:176-186`).

Three later candidates tried to give the QRF chain memory, and each missed:

| Gate-1 candidate | What it adds to the QRF chain | Ten-year autocorrelation, five seeds (reference 0.539, tolerance 0.07) | Result |
|---|---|---|---|
| 1, baseline | nothing: next-period earnings and age | 0.309–0.368 | fails every seed (`runs/gate1_qrf_baseline_v1.json`) |
| 2 | a drawn permanent effect for the person, conditioning every step | 0.615–0.668 | battery fails every seed (`runs/gate1_qrf_latent_perm_v1.json`) |
| 3 | candidate 2 with a permanent-plus-persistent decomposition | 0.632–0.666 | battery fails every seed (`runs/gate1_qrf_latent_perm_v2.json`) |
| 4 | a structural generator with a person component, a persistent component and noise | 0.344–0.367 | fails every seed (`runs/gate1_qrf_structural_v1.json`) |

Two QRF designs with a person effect overshot, and the structural one, which also has a person component, undershot. Tuning persistence inside a QRF chain has not landed in three tries. Adding the frame's other variables (sex, marital status, disability, hours) gives the chain some memory, because those variables do not change from step to step, but only the part of a person's permanent level they explain.

**Whole-career donor splicing.** Copying one donor's whole recorded career, matched at the anchor year, was candidate 5a, which the repository calls MINT-style splicing. Its ten-year autocorrelation ran 0.583–0.639, and it failed the distribution tests in all five seeds. Splicing segments of up to three periods from different donors (5a′) passed the battery in all five seeds and failed the distribution tests in all five (`runs/gate1_splice_v1.json`, `runs/gate1_splice_v2.json`).

### 1.4 The recommended design

Use rank-kNN as the primary method, and let H1 decide among it, a version matched on marital status, and a QRF with the predictors H1 can align across the two data sets. The three are frozen together in the registration, run once together, and adopted by a rule fixed in advance (H-A if it passes, else H-B, else H-C).

Why rank-kNN first:

1. **It is the method that passed.** It is the only earnings-history candidate with a gate-1 pass on the record, under the gate's two amendments (section 1.3).
2. **It keeps a person's place.** AIME averages a worker's 35 best indexed years, so what matters is whether high earners stay high. Microcosm's own design says so: "Earnings histories must preserve rank persistence (AIME is a 35-year order statistic): rank/copula methods across years over single-year marginals" (Microcosm `DESIGN.md:209-210`).
3. **It moves between data sets in ranks.** The anchor is a rank in the frame's own earnings distribution, and earlier years take dollars from the donor data at the same rank. That keeps most level differences between the frame and the PSID out of the history. It does not remove differences in the share with no earnings, and those still carry through.
4. **It anchors on exactly what the frame has.** Gate 1 already scores it as a backcast from one observed year (`scripts/run_gate1_baseline.py:22-36`), which is the frame's situation.

Its weakness is short-lag over-persistence (section 1.3), which H1 checks with two- and four-year cells.

What has to be added, each as a registered change:

- **Anchor convention.** Records come from income years 2022, 2023 and 2024 on the CPS channel, and from the 2015 IRS file uprated on the PUF channel, which holds 58 percent of the weight in Registration 19's frame (`frame_structure.txt`). This plan has not established whether Microcosm carries the 2022 and 2023 amounts to 2024 dollars; `us_runtime/asec_pool.py` pools weights and population and shows no uprating step. So every record is ranked within its source year, channel, sex and five-year age band. That makes the rank independent of the dollar year on each channel: PUF-channel records also carry a source year of 2022–2024 (`frame_structure.txt`), and their amounts may be dated differently from the CPS records'. The rank is then applied in the PSID's 2022 cell.
  - A PUF clone and its CPS source record are separate weighted records. Each gets its own independent history draw.
  - H1's SSA arm scores the same kind of transfer, from an administrative cross-section into the PSID's 2006 cell. It cannot score the CPS and PUF transfer itself, so W2 reports the frame's earnings distributions beside the PSID's by source year and channel.
- **Sex-specific earnings distributions.** Gate 1 fits one distribution per age band and year for both sexes. Gate w1's third candidate split the interior bands by sex and found no collateral damage (`models/transport_deployment_v3.py:34-43`). Histories for the frame do the same.
- **Ages and years outside gate 1's range.** Gate 1 scores ages 25 to 59 and income years 1998 to 2022 (`gates.yaml:50-58`). A frame person who is 70 in the start year has a career that began around 1976. Years 1968–1996 are annual in the PSID, and the generator steps one year at a time there. H1 scores whole careers, so it covers this extension.
- **Covered, capped earnings.** PSID labor income is converted to a share of each year's wage base and capped at 1, the step gate_epuf_fill defines (`docs/amendments/gate_epuf_fill_registration_proposal.md`, section 3, on branch `epuf-career-fill-20261003`).
  - Work outside Social Security coverage is a separate gap. The repository has a draft design that would classify each person-year's earnings as covered wages, covered self-employment, uncovered or unresolved (`docs/design/covered_earnings_correction.md`, draft revision 2, which authorizes no implementation).
  - Until it lands, histories treat all labor income as covered up to the wage base, as the PSID projection does.

**The two other candidates:**

- **Rank-kNN with marital strata (H-B).** It restricts donors to the person's sex and marital group, and adds no other constant. Education would join by amendment once the frame carries it (section 5.4).
- **QRF with the predictors H1 can align across the PSID and the frame (H-C).** It uses age, sex, anchor-year earnings, marital status, disability, hours and self-employment.
  - It runs once as a registered comparison, so the answer to "why not a QRF?" rests on a scored run on the same held-out data.
  - Occupation and class of worker are left out because their codes differ across the PSID's years and the frame.
  - Year of entry is left out because the PSID holds too few immigrants to learn from.

### 1.5 Years the PSID cannot supply

The career assembler fills two kinds of gap with fixed rules: each odd year after 1996 is the mean of its neighbors, and nothing counts before 1968 or before age 22, whichever is later (`docs/amendments/gate_epuf_fill_registration_proposal.md`, "What this gate is, in plain words"). Max approved the direction of learning replacements on EPUF on 3 October: "at a minimum seems like we could use it to improve the odd-year filling, we're overstating that form of persistence with our current method" (same document). Gate_epuf_fill scores those fills on EPUF people no fill has seen. Its tolerance awaits Max's ruling (d927), and pull request #516 adds the candidates.

Frame histories use whichever fills gate_epuf_fill certifies. If none is certified, they use the current rules and carry that label. For people born before 1946, whose careers began before 1968, the pre-1968 fill carries much of the career, and H1 reports its cells by birth cohort so that shows.

### 1.6 People already receiving benefits

For a retired worker in the frame, the benefit in payment equals the PIA, reduced or increased for the claim age, with every COLA since entitlement.

- **Claim age.** The frame does not record it. We infer it the way the engine already assigns claim ages, from SSA's distribution of retired-worker awards by sex and year of entitlement (`paper/paper.qmd:151`).
- **The inferred PIA.** Dividing the benefit by the matching adjustment and COLA factors gives the PIA.
- **Disabled workers** need no claim-age adjustment.

The inference has limits. W2 names each, and counts the records it touches where the frame can identify them; where it cannot, the limit is reported as unquantified:

- **Dual entitlement.** A CPS retirement amount can include a spouse's excess.
- **Survivors and spouses.** Their benefit depends on their own claim-age reduction, the limit tied to the deceased worker's claim age, and the offset against their own benefit. A widow(er)'s benefit therefore does not invert the same way. The first version therefore does not infer a spouse's or survivor's linked worker PIA: their benefit is kept as state, and any rule that needs the linked PIA is counted as unsupported for them.
- **Medicare premiums.** Amounts may be reported net of the Medicare Part B premium, as exercise 2's named differences note (`uniform_cut_track_u/runner.py:121-124`).
- **Partial years.** Receipt can begin partway through the year.
- **WEP and GPO.** Benefits for income years 2022–2024 can reflect the windfall elimination provision and government pension offset. The Social Security Fairness Act repealed both for benefits after December 2023.
- **Synthetic splits.** Registration 19 found that 16.9 percent of the frame's beneficiaries, by weight, carry a fixed-proportion split across all four Social Security components from the PUF channel. For them the benefit type is not observed.

W2 checks inferred PIAs against SSA's published average PIA by age and sex for retired workers (Annual Statistical Supplement, Table 5.B1). When a beneficiary needs a history for grouping (lifetime earnings quintiles, as MINT reports), it is generated with the inferred PIA's rank as the anchor in place of current earnings. Those histories do not change the beneficiary's benefit.

### 1.7 Couples

Spouse and survivor benefits depend on both spouses' records, and spouses' careers are correlated. Histories built one person at a time keep only the correlation that runs through the two spouses' start-year ranks.

- **What gate 2c covers.** It scores marital status jointly with earnings on PSID couples (`runs/gate2c_hazard_v2.json`).
- **What H1 adds.** Its PSID arm has two couple cells: the median ratio of the lower earner's career earnings to the higher earner's, and the share of couples where that ratio is below one half. That share is where spousal benefits and dual entitlement bite.
- **If the cells fail.** A later candidate draws couples' histories jointly from PSID couples.

### 1.8 Earnings after the start year

Track B owns forward earnings, and this plan does not duplicate it. The forward law is a rank chain fitted on PSID earnings through 2014 at ages 25 to 64. It converts ranks to dollars with an average-wage-index trend it fits on 2005–2014, and it has no fitted distribution above 64 (`paper/paper.qmd:168`). It passes gate m6 in 4 of 5 seeds (`runs/gate_m6_candidate3_v1.json`).

A Microcosm start asks four things of Track B, which its design should take as requirements:

1. **A start state from a frame person.** The law builds each person's starting state at its boundary year, 2014.
   - **What it needs.** Realized 2014 earnings and a permanent-rank estimate, `u_w`, fitted over the person's whole positive history (`_fit_u_w`, `engine/forward_earnings.py:697-739`, mixed in at 0.1 at line 1533). It refuses anyone without them. It keeps the earnings two years back if they were observed and leaves them missing otherwise, and its first draws do not condition on them (`engine/forward_earnings.py:1411-1463`).
   - **Outside that support.** The engine gives fixed zero earnings to people who lack the state (`engine/earnings_domain.py:1-7`).
   - **For a frame person.** The same pieces can be computed at the frame's start year from the start-year earnings and a generated history.
2. **The same rank space, or a mapping.** The two models share the k-nearest-neighbor constants (25 neighbors; weights 1, 0.5 and 0.25; the 0.1 blend; `engine/forward_earnings.py:64-77`) but not the rank space.
   - The forward law ranks within eight wage-index-normalized age bands pooled over years through 2014 (`fit_age_marginals`, `engine/forward_earnings.py:486-524`).
   - The backward generator ranks within age band and year (`scripts/run_gate1_candidate7.py:29-35`).
   - A permanent-rank estimate taken from a generated history is also not what the law was fitted on.

   The hand-off needs a stated mapping. H1's PSID arm reports how well `u_w` estimated from a generated history matches `u_w` from the same person's real one (report-only).
3. **A new boundary year is a refit.** Starting the law from 2024 instead of 2014 means fitting it again. Gate m6's certification does not carry over, and the refit needs its own gate, which belongs to Track B.
4. **The projection's own wage index and ages 62 to 69.** From a 2024 start, ranks should convert to dollars with the selected baseline's average wage index, from the 2026 Trustees Report or CBO's 2026 projections (pull request #512), not a 2005–2014 trend. The earnings test needs earnings at ages 62 to 69, beyond the law's fitted range. The paper already plans a law fitted on ages 25 to 69 (`paper/paper.qmd:382`).

Until Track B delivers, a Microcosm start runs only on invented data. Any real-data run without forward earnings would carry Track A's label ("no earnings after the start year") and would understate the AIME of people who claim in the following years.

## 2. Non-wage income and wealth

### 2.1 What the PSID supplies today

Only one of the four tests against DYNASIM3 reads non-wage income or wealth, and it is not a projection.

- **Exercise 2, the 13 percent cut.** It counts the PSID's reported family money income and turns the family's PSID wealth into an annual income stream priced on NCHS 2000 life tables (`uniform_cut_track_u/runner.py:100-150, 216-218`; `cohorts/age67.py:86-98`).
- **Exercises 1 and 3.** They report mean Social Security benefits by age. Their code paths read no wealth, pension, interest, dividend or asset variable; a search of `cola_track_a/`, `fra68_track/`, `track_a_v2/`, `cohorts/psid2010.py` and `engine/` finds none.
- **The illustrative households.** They set pensions and savings by hand.

So nothing in the projections uses non-wage income or wealth yet. It starts to matter when the projected population goes through PolicyEngine-US, where it decides income taxes on benefits, SSI eligibility, SNAP, Medicaid and poverty.

### 2.2 The Microcosm variables that replace it

From the column lists of Registration 19's frame (`frame_structure.txt`), with the stage that produces each:

| Income or wealth item (exercise 2's PSID concept) | Microcosm frame variables | Where Microcosm gets it |
|---|---|---|
| Earnings | `employment_income_before_lsr`, `self_employment_income_before_lsr` (person) | CPS reports on CPS records (`WSAL_VAL`, `SEMP_VAL` carried raw); the 2015 PUF on the PUF channel. The anchor for histories |
| Social Security | `social_security_retirement`, `_disability`, `_survivors`, `_dependents` (person) | CPS reports on CPS records (`SS_VAL` and the reasons `RESNSS1`, `RESNSS2` carried raw); the PUF on the PUF channel, where 16.9 percent of beneficiaries by weight carry a fixed-proportion split across all four (Registration 19, named difference 5). Calibrated to SSA dollars by type. After the start year the engine's computed benefits replace them |
| SSI | computed by PolicyEngine-US; `takes_up_ssi_if_eligible` (person) | Take-up from CPS reports and SSA counts (stage `ssi_take_up`); the CPS report `SSI_VAL` is also carried |
| Defined-benefit pensions and annuities | `taxable_private_pension_income`, `tax_exempt_private_pension_income` (person) | The PUF on the PUF channel (stage `puf_tax_detail`); on CPS records the frame also carries the CPS reports (`PNSN_VAL`, `ANN_VAL`) |
| Retirement-account withdrawals | `taxable_ira_distributions`, `tax_exempt_ira_distributions`, `taxable_401k_distributions`, `taxable_403b_distributions`, `taxable_sep_distributions`, `keogh_distributions` (person) | CPS records, imputed by QRF onto the PUF channel (stage `retirement_distributions`) |
| Asset income | `taxable_interest_income`, `tax_exempt_interest_income`, `qualified_dividend_income`, `non_qualified_dividend_income`, `rental_income`, `s_corp_income`, `partnership_income`, `estate_income`, capital-gains variables (person) | The PUF (stage `puf_tax_detail`) |
| Veterans' pensions, unemployment, workers' compensation | `veterans_benefits`, `unemployment_compensation`, `workers_compensation` (person) | CPS reports, carried raw beside them (`VET_VAL`, `UC_VAL`, `WC_VAL`); workers' compensation from stage `workers_compensation_input` |
| Child support, alimony, other | `child_support_received`, `alimony_income`, `miscellaneous_income` (person) | Child support from the CPS (stage `child_support_inputs`); alimony and other income from the PUF |
| Family wealth (PSID `WEALTH1`) | `net_worth` (household) | A QRF anchored on the SCF 2022's net worth (stage `scf_wealth`) |
| Liquid assets | `bank_account_assets`, `stock_assets`, `bond_assets` (person, on the household's head) | Stage `scf_wealth`; the SIPP and SCF blend is current `main`, unconfirmed for this frame (Registration 19, named difference 1) |
| Vehicles and auto loans | `household_vehicles_value`, `auto_loan_balance` (household) | SIPP 2023 (stage `vehicle_assets`); SCF |
| Employer DC balances (exercise 2's row U7), home value | none | The SCF components are used in construction and not exported; a gap for any wealth result that needs them |

Neither the W1-pinned sparse frame nor the dense build has the liquid assets or `net_worth`. Both also lack `taxable_401k_distributions`, `veterans_benefits`, `workers_compensation`, `child_support_received`, `alimony_income` and `takes_up_ssi_if_eligible` (`frame_structure.txt`). The start therefore needs a release that has them (section 5.1).

### 2.3 How they age forward

Nothing in the model projects wealth forward today. The first version keeps the rule simple enough to test:

1. **Growth.** Each dollar amount grows each year by the factor the selected baseline implies for it: wages for earnings-like items, prices for pensions with COLAs, and PolicyEngine-US's own uprating series elsewhere. That way a projected population and Microcosm's static aging agree on aggregates where they should (Microcosm `docs/us-annual-static-aging.md`).
2. **Life-cycle position.** Each unit keeps a fixed rank within its cell for each item, and takes that rank's value as it ages into the next cell. The value comes from the start-year frame's distribution for that cell, grown as in step 1.
   - Person items rank among persons, within sex and five-year age band.
   - Household items (net worth, and the liquid assets that sit on the head) rank among households, within the head's sex and five-year age band and household type (couple or single).
   - Ranks inside a zero mass break by a uniform draw keyed by the unit's id, fixed for the projection. Pensions begin as a unit ages into cells where fewer have none.

   This uses the cross-section's age profile as each cohort's future, which overstates defined-benefit pensions for younger cohorts.
3. **Events.** These change ranks.
   - When a spouse dies, the survivor keeps the household's assets.
   - When a single person dies, their assets leave the population.
   - From the start year on, Social Security income is the engine's computed benefit, and SSI, SNAP, Medicaid and taxes come from PolicyEngine-US each year.

The check A1 (section 3) applies the same rule to the PSID's wealth and income panels and reports how far it misses. It stays report-only until its floors show it can tell a good rule from a bad one, the path gate_epuf took (`docs/amendments/gate_epuf_registration_proposal.md`). The repository reads PSID wealth only for waves 2005–2013 (`cohorts/age67.py:94-98`), so A1 needs readers for the other waves (task T3).

### 2.4 What this does not do

It models no saving or spending decisions, no asset spend-down to qualify for SSI or Medicaid, no inheritance between generations and no response of retirement accounts to markets. A projection that reports results by wealth or by asset tests carries that label.

## 3. Tests

Three terms recur below:

- A **floor** is the gap between two disjoint samples of real data. It sets how far a result can move by chance.
- **Bite** is a check that a method known to be wrong fails the test.
- A **partition** splits a test's cells, before anything is scored, into those that decide pass or fail and those only reported.

The **effective sample size** (Kish) is the number of equally weighted people a weighted sample is worth.

### 3.1 What existing gates cover

| Part of a Microcosm start | Test today | What it leaves open |
|---|---|---|
| Earnings dynamics learned from the PSID | gate 1 passes, under two amendments (`runs/gate1_rank_knn_v5.json`) | Scores 1998–2022 and ages 25–59, pooled over sex, on PSID people's own anchors (`gates.yaml:50-58`); never frame people or whole careers |
| Filling years the PSID did not record | gate_epuf_fill, registered and unlocked (pull requests #515, #516; d927) | Certifies fills on EPUF's concept, not the PSID-to-SSA gap |
| PSID earnings against SSA records | gate_epuf, report-only (#509) | Gates nothing |
| PSID processes carried onto the frame | gate w1 passes (`runs/gate_w1_candidate4_v1.json`) | Scores cross-sectional joints; certifies no transition and no history (`paper/paper.qmd:362`) |
| Forward earnings | gate m6 passes 4 of 5 seeds (`runs/gate_m6_candidate3_v1.json`); Track B's B2 awaits d765, d781 and d782 | Fitted through 2014, ages 25–64; a 2024 boundary needs a refit and its own gate |
| Marriage, households, marriage by earnings | gates 2, 2b and 2c pass, 4 of 5 seeds each | Not yet inside a projection |
| Disability | gate m4 passes 5 of 5 seeds; SSDI entitlement not gated | |
| Mortality, claiming | not gated | |
| Benefit rules | the Python oracle; Axiom matches its AIME for 7,486 of 7,486 people (`paper/paper.qmd:182`) | |
| **Histories for frame people** | none | New gate H1 |
| **The starting stock of beneficiaries and their inferred PIAs** | none | New check W2, report-only |
| **The projection's first year from the frame** | none; `gates.yaml` names gate 3 for near-term outputs but gives it no cells (`gates.yaml:2898-2905`) | Gate 3's first cells |
| **Income and wealth aging** | none | New check A1, report-only |
| **Projected population through PolicyEngine-US** | Registration 19's report-only design | Registered per analysis, as Registration 19 was |

### 3.2 New tests

Each test is drafted in full in the [draft registration](microcosm-start-registration-draft.md). In short:

- **H1, earnings histories for a cross-section (gate).** Can a method, given only what the frame observes in one year, produce careers that look like real ones?
  - **The SSA arm.** It hides every year of EPUF careers except 2006 and rebuilds them from 2006 earnings, sex and birth year, the way the plan deploys: PSID donors matched by rank, years the PSID lacks filled by gate_epuf_fill's certified procedure refit on H1's own training part, and conversion to capped shares of the wage base. It scores the rebuilt careers on people nothing learned from. The split is new, salted differently from gate_epuf_fill's, so it does not reuse a test set that gate will have published. A report-only configuration with EPUF donors shows how much of any miss comes from the PSID itself.
    - **Cells:** what the benefit formula reads, by sex and age: the distribution of top-35-year indexed earnings, the share of years with no earnings, the share at the taxable maximum, insured status, and the correlations of the anchor year with the career and with years two, four and ten earlier.
    - **What a pass certifies:** the deployed procedure on SSA's records and on the PSID, but not the transfer of ranks from CPS or PUF records, which W2 reports.
    - **Tolerance:** the sampling error the frame itself carries in each cell. A method passes only if its error is no larger than what the frame's own sample would introduce.
  - **The PSID arm.** It does the same on PSID families held out by new splits, from 2022 earnings, age, sex, marital status, disability, hours and self-employment.
    - **Cells:** the same features, plus cells by marital status and disability and the couple cells of section 1.7. Reported only: cells by education, which show what leaving education out costs, and the agreement of the forward law's `u_w` between real and generated histories.
    - **Tolerance:** from pairs of real held-out-size samples, the way gate 1 prices its geometry thresholds.
    - **Disclosure:** gate 1 selected rank-kNN on these same people, and gate_epuf_fill selected its fill procedure on EPUF people who overlap the SSA arm's test set. The registration says both.
  - **Candidates.** All three are frozen in the registration, scored in one run, and adopted by the rule in section 1.4.
- **Gate 3, the first projected year (gate).** Project the frame one year forward. Score the projection's growth in retired- and disabled-worker counts and average benefits, measured as the frame measures them, against the growth in SSA's December figures. Comparing growth cancels the stable part of the gap between the frame's concept and SSA's. It does not cancel errors in the frame's makeup that change deaths, widowhood or claims, which gate 3 scores along with the engine. The cells are fixed now, and the partition comes from the start-year frame alone. Gate 3 locks separately from H1, after the engine exists and engines with no mortality or no new awards fail on an invented frame.
- **W2, the starting population against SSA's records (report-only).** Do the frame's beneficiaries, with their inferred PIAs, match SSA's December counts and averages for the start year by type, age and sex? These are Annual Statistical Supplement tables 5.B1, 5.D1 and 5.G1; the evidence folder holds a capture of the 2023 edition (`~/microcosm-launch-evidence/dynasim-parity-20260909/ssa-supplement-2023/`). Microcosm calibrates Social Security dollars by type but not beneficiary counts (Registration 19), so counts and average PIAs are held out.
- **A1, income and wealth aging (report-only).** Apply section 2.3's rule to PSID families' wealth and income at one wave, and compare with what the PSID recorded four years later, by age band.

### 3.3 How the tests get fixed before anything runs

The registration fixes each test's question, held-out data, split, cells, statistics, tolerance rule, pass rule and H1's candidates. The tolerance multipliers it proposes are drafts until Max ratifies them at lock, as he is ruling on gate_epuf_fill's (d927). After posting:

1. **Floors.** They come from real data only, and no candidate is scored.
2. **Partition and bite.** The partition is fixed before any candidate runs. Then a method known to be wrong must fail by a clear margin (gate 1's failed QRF baseline for H1, on data no scored seed holds out; engines with no mortality or no new awards for gate 3, on an invented frame). A test with no bite does not lock. Gate 3 goes through this step later than H1, once its engine exists.
3. **Review and lock.** Referee rounds independent of the drafter, then Max's ratification, then the block enters `gates.yaml` locked.
4. **The run.** After gate_epuf_fill's verdict, a second comment posts the registered commit, the fill procedure that verdict selects, and a forecast for each candidate, and H1's candidates run once, together.
5. **No early projection.** The first projection of the real frame is gate 3's registered run. The engine adapter is built on invented data until then.

### 3.4 Properties the code must hold

The tests above score results. The code that produces them also has properties that hold for every input, and each becomes a property-based test (Hypothesis) beside the example tests, run on invented data:

- **Histories.**
  - Every returned share of the wage base is finite and in [0, 1]; in the PSID arm, every returned dollar amount is finite and non-negative.
  - The anchor year comes back unchanged, and no year outside the person's career window is written.
  - The same inputs and seeds give the same history.
  - No history has earnings before the person's drawn year of US entry (section 5.4).
- **Ranks.** For positive earnings between the 0.001 and 0.999 quantiles of a fitted distribution (the clamps the rank machinery uses), converting dollars to a rank and back returns the same dollars.
- **Inferred PIAs.**
  - The unrounded inverse is exact: applying the unrounded claim-age adjustment and COLA factors to an inferred PIA returns the frame's monthly amount to floating-point precision.
  - With the statute's rounding, the result is within that rounding.
  - No inferred PIA is negative.
- **Weights.** In a projection without entrants, the total weight in a year equals the previous year's total less the weight of the people who died. Nothing else changes a weight.
- **Aging rule.**
  - Between events, each unit's rank within its cell carries over from year to year.
  - Growing a whole cell by a factor multiplies its quantiles by that factor.

The dynamics oracle's AIME and PolicyEngine-US's `ss_aime` are two implementations of related rules, but not the same rule:

- PolicyEngine-US caps total earnings including raw self-employment income, which can be negative.
- It looks back at most 45 years before the current year (`variables/gov/ssa/social_security/ss_aime.py`; `parameters/gov/simulation/aime_lookback_years.yaml`).

Comparing them is therefore a reported differential (task T13), not a property. Each disagreement is reduced to its smallest case and attributed before anyone calls it a bug in either.

## 4. Order of work

### 4.1 What has to land first

- **gate_epuf_fill.** Max's ruling on its tolerance (d927), then its lock, then pull request #516's candidates and the one reading of its test data. Frame histories use the fills it certifies (section 1.5). H1's registered run waits for that verdict, because H1's deployed configuration uses the certified fill procedure (or the current rules, if none is certified), refit on H1's own training part. The frame itself uses gate_epuf_fill's own fit.
- **Track B.** Max's rulings on d765, d781 and d782, then B2's registration, then forward earnings in the projections (months 2 to 5), then a refit of the law at a 2024 boundary with its own gate (section 1.8). The history work (tasks T1 to T7 below) does not wait for Track B; any real-data projection from the frame does.
- **Pull request #512**, which makes the 2026 Trustees Report and CBO's 2026 projections selectable as the projection's baseline, merged on 4 October 2026 (`ff3fe306`). A 2024 start needs one of them. The 2008 Trustees path that the DYNASIM3 tests use stops at 2030 and predates every year the frame describes (Registration 18).
- **Four requests to Microcosm** (sections 5.1 and 5.4):
  - restore educational attainment to the US release;
  - keep the previous year's wages, which its CPS panel link already recovers for matched records;
  - explain the marital makeup of older beneficiaries;
  - publish a dense release that carries this plan's columns: the liquid assets, `net_worth`, the income items of section 2.2, the derived disability, self-employment, hours and weeks variables, and the prior-year flag.

  None of these blocks the first candidate. Education blocks the education cells, and the dense release limits the precision of every cell.

### 4.2 Tasks

Effort is in agent-days of build work and days of human review. Every figure is an assumption, not a measurement.

| # | Task | Depends on | Agent-days | Review days |
|---|---|---|---:|---:|
| T1 | Pin the frame and write its reader: the person table of section 1.2, spouse links, source year, support channel and weights; a refusal of the real frame outside registered entry points; tests on invented data | the frame choice (decision 2) | 3–5 | 1 |
| T2 | File the four Microcosm requests with evidence | — | 1–2 | 0–0.5 |
| T3 | PSID readers: annual hours, self-employment, education, and wealth for 1999–2021 | — | 4–6 | 1 |
| T4 | H1's floors, partition, bite checks and block draft; two referee rounds | the posted registration, T3 | 8–12 | 3–4 |
| T5 | H1's three candidates and strawman, built on invented data | T4's interfaces | 8–12 | 2–3 |
| T6 | H1's lock and its one run, after the second comment | T4, T5, d947, gate_epuf_fill's verdict | 2–4 | 2 |
| T7 | The starting stock: benefits as state, inferred PIAs for retired and disabled workers and their named limits, spouse and survivor links; gate 3's partition from the start-year frame (standard deviations only); then W2's first run | T1 | 6–9 | 2 |
| T8 | Run the existing engine on frame people, on invented data: starting states, fixed trajectory weights, the selected baseline | T1, T6, T7, #512 (merged) | 10–15 | 3–4 |
| T9 | Connect Track B's refitted forward law from the frame's start state | T8, Track B | 4–6 | 1–2 |
| T10 | Income and wealth: the table of section 2.2, the aging rule, A1 | T1, T3, T8 | 6–10 | 2–3 |
| T11 | Gate 3's bite check on an invented frame with the T8 engine, Max's ratification and gate 3's lock comment, SSA captures for December of the start year and the next, and the registered run | T8, T9 | 5–8 | 2 |
| T12 | Each projected year through PolicyEngine-US, split by level of government, each analysis registered | T11, T10; Registration 19's machinery | 8–12 | 2–3 |
| T13 | Differential checks, reported: the oracle's AIME against PolicyEngine-US's `ss_aime` on the same histories; a PSID start against a Microcosm start in a common year; dynamic against static aging aggregates | T6, T11 | 5–8 | 1–2 |
| | **Total** | | **70–109** | **22–29.5** |

### 4.3 Where it sits in the 24-month plan

| When | Work | 24-month plan item it serves |
|---|---|---|
| October–December 2026, before funding | T1–T7 | none yet; this is the part that can start now |
| Months 0–5 | T8, T10, T13 | beside "forward earnings in the projections" (months 2–5) and the earnings test and family maximum (months 2–4) |
| Month 5 onward | T9 | as Track B's refitted law lands |
| Months 5–9 | T11, T12 | "projected population through PolicyEngine: federal, state, local" (months 5–9), now starting from Microcosm |

This changes one assumption of the PlanGraph draft. Its months 5 to 9 item is "built on the current projections", which start from the PSID. On this schedule it starts from Microcosm instead, without the kernel port. It still depends on the earnings test and family maximum (`ret-famax`) as the draft has it.

The registered real-PSID population run (d727, months 2 to 4) is unchanged. It is a static analysis of PSID people and needs no projection.

## 5. Risks

### 5.1 Weights and which release to use

- **Concentration.** The frame gate w1 pins has 166,302 people, but its weights give an effective sample size of 14,328, with one household weighing 433,329 (`gates.yaml:4345`).
  - Registration 19's frame has 166,321 people and an effective size of about 27,000.
  - A dense Microcosm build from 8 July 2026, before pruning, has 865,046 people and an effective size of about 180,000 (`populace-us-2024-buildh-dense-warmstart-b449eb7`).

  These figures come from household weights alone (`docs/plans/microcosm-start-evidence/frame_structure.txt`, from the script beside it). The same computation reproduces gate w1's 14,327.8 exactly.
- **No release has both.** No release checked has both the dense build's precision and the columns this plan needs. The dense build lacks the liquid assets, `net_worth`, several income items, the derived disability, self-employment, hours and weeks variables, the marital detail and the prior-year flag (sections 1.2 and 2.2), and so cannot run section 2.2's income and wealth. It does carry the raw CPS columns behind most of section 1.2 (`A_MARITL`, `PEDIS*`, `WKSWORK`, `HRSWK`, `SEMP_VAL`, `PEIO1COW`, `PEINUSYR`), so histories could be matched on it with registered constructions. Registration 19's frame has the columns at about a seventh of the dense build's effective size. A projection that follows people into small groups (widowed men at 62 to 64, long disability spells) needs both. Decision 2 asks which to use until Microcosm publishes a dense release with the columns.
- **Tolerances follow the frame.** H1's SSA arm prices each cell at the frame's effective size, so moving to a denser frame tightens every tolerance. The registration re-derives them before any further run.
- **Clones.** In Registration 19's frame, 58 percent of the weight sits on records from the PUF-support channel (`frame_structure.txt`). In the dense build, every CPS record has a PUF clone. 16.9 percent of beneficiaries by weight carry a synthetic fixed-proportion split across all four Social Security components (Registration 19, named difference 5). For them the benefit type is not observed, and section 1.6's PIA inference is weak. W2 reports its cells with and without them.
- **Marital makeup.** The frame's beneficiaries aged 62 and over are 85.6 percent married, against about 60 percent in a MINT tabulation for 2022 (Registration 19, named difference 6). Spouse and survivor benefits rest on this. No spouse or survivor result from a Microcosm start should be published until Microcosm explains or fixes it; the request in T2 asks.
- **Weights over time.** Microcosm's design gives each trajectory one weight and stacks later years' targets on it (Microcosm `DESIGN.md:125-128`).
  - **The first version.** It holds each person's start-year weight fixed, as the PSID projection holds the 2011 weight.
  - **It closes.** With no births or immigrants until those models enter the projections, the projected population closes. Everyone 50 and older in 2030 was alive and in the frame in 2024, apart from later immigrants. So 2030 results by age for older people are covered; younger groups are not.
  - **No static aging on top.** PolicyEngine-US's own extension of the frame to later years grows weights with population and keeps ages fixed (Registration 19, "Year"). That is static aging, and a dynamic projection must not apply it on top.
- **Version drift.** Registration 19's frame was weighted under PolicyEngine-US 1.764.6 and runs under 2.18.0 (named difference 7). Each run records both.

### 5.2 A 2024 population against a 2010 test start

Exercises 1 and 3 start in 2010 because DYNASIM3's published reforms do. Microcosm's frame describes 2024, pooled from income years 2022 to 2024. There are four ways to handle this:

- **A. Leave the DYNASIM3 tests on the PSID start (recommended).** Their one-shot runs are spent and public, so a Microcosm-start rerun would be post hoc in any case. The Microcosm start serves the comparisons that start in the 2020s: OACT's, PWBM's, MINT's and CBO's tables on the 2026 basis, which the 24-month plan schedules for months 12 to 15, and gate 3's near-term cells.
- **B. Compare the two starts in a common modern year.** Project both a PSID start from its 2023 wave and the Microcosm start from 2024 to 2030 under the same baseline, and report where they differ (T13). It isolates what the starting population does, on a horizon both can reach.
- **C. Build a 2010 Microcosm frame** from the 2011 CPS supplement and contemporaneous IRS and SCF files. It would allow a like-for-like rerun of exercises 1 and 3. Microcosm's pins tie the US pool to income years 2022–2024, the 2015 PUF, the 2022 SCF and the 2023 SIPP (the frame's `source_year`; `source_stages.json`), so a 2010 vintage needs new pins and inputs for every stage. It is months of Microcosm work for a post hoc result.
- **D. Wind the 2024 frame back to 2010.** Rejected. The people who died between 2010 and 2024 are missing, immigrants who arrived after 2010 are present, and cohort-specific rules (the FRA schedule by birth year) would apply to the wrong cohorts.

### 5.3 Benefit rules in PolicyEngine-US

PolicyEngine-US 2.24.1 (upstream `main` `a39cfa7136`) splits Social Security into what it computes and what it takes as given:

| Rule | PolicyEngine-US | The dynamics oracle |
|---|---|---|
| Benefits by type (retirement, disability, survivors, dependents) | Inputs with no formula; `social_security` adds the four (`variables/gov/ssa/ss/social_security.py`, `social_security_retirement.py`) | Computed |
| AIME and PIA from an earnings history | Computed in a separate path: `ss_aime` reads up to 45 prior years of `employment_income` and `total_self_employment_income`, capped at each year's wage base, or takes `ss_aime_input`; `ss_pia` applies the formula (`variables/gov/ssa/social_security/ss_aime.py`, `ss_pia.py`; `parameters/gov/simulation/aime_lookback_years.yaml`) | Computed (`cola_track_a/benefits.py`) |
| Claiming adjustment, earnings test | Computed in the same path (`ss_retirement_age_adjustment_factor.py`, `ss_earnings_test_reduction.py`, `ss_retirement_benefit_before_earnings_test.py`) | Adjustment computed; earnings-test parameters held, not applied (`paper/paper.qmd:172`) |
| Spouse, survivor and child benefits, family maximum, dual entitlement | Not modeled | Spouse and survivor benefits computed in the projections; the family maximum and dual-entitlement reductions are in Track B's gross-benefit layer (`track_b/gross_benefits.py`), tested on SSA's worked examples (`tests/test_track_b_gross_benefits.py`), and not yet used by a projection |
| Taxation of benefits | Computed (`variables/gov/irs/income/taxable_income/adjusted_gross_income/irs_gross_income/social_security/`), with the revenue credited to OASDI and Medicare (`variables/gov/ssa/revenue/tob_revenue_*.py`) | Not modeled |
| SSI | Computed, with income deeming from an ineligible spouse or parent (`variables/gov/ssa/ssi/eligibility/income/deemed/`); no resource deeming (`variables/gov/ssa/ssi/eligibility/resources/` holds only the resource test and countable resources) | A static offset in exercise 2 only |

No variable outside `variables/gov/ssa/social_security/` reads `ss_pia`, `ss_earnings_test_reduction` or `ss_retirement_benefit_before_earnings_test`. PolicyEngine-US's own benefit path therefore does not feed the components its other programs read.

**What this means for the plan.** The dynamics engine computes the benefits and hands PolicyEngine-US the four components each year, as the illustrative households do now. PolicyEngine-US then computes taxes on benefits, SSI, SNAP, Medicaid and state programs.

**SSI gaps.** Registration 19 named two SSI gaps under PolicyEngine-US 2.18.0: no deeming of an ineligible spouse's resources, and a cap on deemed-income benefits that differs from the regulation (named differences 3 and 12). The first still holds at 2.24.1. The second has not been rechecked at 2.24.1.

### 5.4 Other risks

- **No education in the frame.** None of the Microcosm US releases checked carries educational attainment: not the W1 pin, not Registration 19's frame, not the dense build. Both source surveys record it (the CPS's `A_HGA`, the ACS's `SCHL`), and Microcosm already restores reviewed CPS person columns from the pinned Census files (Microcosm `docs/us-asec-census-person-columns.md`). Until it adds this one, no candidate uses education and H1's education cells are report-only.
- **Three income years, two sources.** CPS records carry earnings for income years 2022, 2023 or 2024, and this plan has not established whether Microcosm carries them to 2024 dollars. PUF records carry the 2015 IRS file's earnings, uprated, with a source year of 2022–2024. Section 1.4's anchor convention ranks within source year and channel, so neither question changes a rank. W2 reports by source year and channel.
- **Ages top-coded at 80 and 85.** The frame stores ages 80–84 as 80, and 85 and over as 85. Mortality, widowhood and survivor timing need single years, so the starting age within each band is drawn from SSA's population by single year, under a registered rule.
- **Immigrants.** The frame carries year of entry (`PEINUSYR`), as a grouped code. A history starts no earlier than a year drawn uniformly within the person's entry-year group, keyed by person id, under the CPS's code definitions captured with the frame pin. Recent immigrants therefore have short US careers, as SSA records them.
- **Uncovered work.** Some state and local government workers are outside Social Security. The frame carries class of worker (`PEIO1COW`), but the PSID does not separate covered from uncovered work in most years. The repository's covered-earnings correction is a draft design, not code (`docs/design/covered_earnings_correction.md`). Until it lands, a current government worker's whole history counts as covered, which overstates benefits for workers outside the system.
- **People in institutions.** The CPS leaves out people in nursing homes and other institutions, many of them old beneficiaries. W2's counts by age show the gap.
- **Restricted data and compute.** The frame carries values imputed from the IRS Public Use File. Registration 19 runs it on Modal under a ruling specific to that analysis (d806). The parked d093 asks only whether restricted PUF inputs may go to Modal, so no ruling covers this plan's runs. The draft registration runs W2 and gate 3 locally unless Max rules otherwise.
- **Blinding.** None of these tests needs a sealed comparator. Any later blind test that needs a projected population waits until the projection gates pass (`paper/paper.qmd:396`), and its builders are briefed on `RESTRICTED-FILES.md`.

## Decisions needed

1. **Post the registration?** This is the go to post the draft registration on issue #42, after the independent review this plan's pull request records. It fixes H1, gate 3's cells, W2 and A1, and H1's candidates and adoption rule, before any code. It is queued as d947, and nothing is posted before Max's go.
2. **Which frame for dynamics?** The candidates:
   - Registration 19's release has the columns at an effective size of about 27,000.
   - The dense build has about 180,000 but lacks the columns.

   This plan recommends Registration 19's release for H1's tolerances and the first runs, and asking Microcosm for a dense release with the columns (T2). Moving to it later would re-derive the tolerances. This is a methodology choice with more than one defensible answer.
3. **Tolerance multipliers.** H1's K and k, and gate 3's constants, are drafts. Max ratifies them at lock, as for gate_epuf_fill (d927).
4. **The 2010 question.** Section 5.2 recommends options A and B, and not C, for now.

## Sources

- **Pinned commits.** Code and artifacts are cited at microcosm-dynamics `master` `492d5a60f`, Microcosm `main` `48fa06166`, and PolicyEngine-US `main` `a39cfa7136` (2.24.1). Package paths are under `src/populace_dynamics/` unless stated, and Microcosm's `us_runtime/` paths are under `packages/microcosm-build/src/microcosm/build/`.
- **Registration 19** is issue #42 comment 5961843703.
- **The 24-month plan** is the NASI backup slide (`~/nasi-2026-slides/app/slides/MilestonesSlide.tsx`) and its PlanGraph source (`~/microcosm-launch-evidence/nasi-meeting-20261001/plangraph/`), both local to Max's machine.
- **Frame structure** (column lists, source years, support channels, and effective sample sizes from household weights) was read from cached Hugging Face files by `docs/plans/microcosm-start-evidence/frame_structure.py`. Its output, with each file's revision and SHA-256, is `docs/plans/microcosm-start-evidence/frame_structure.txt`. It summarizes no outcome variable.
- **The independent review** of this plan, and the response to it, are in `~/reviews/microcosm-start-plan-20261004/review/`.
