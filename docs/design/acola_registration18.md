**Registration 18: trust fund test A-COLA. The 2030 cost effect of OACT provision A1 ("Starting December 2027, reduce the annual COLA by 1 percentage point") against OACT and PWBM, with MINT5 as a third comparator. One-shot, report-only, blind by procedure, not gated.**

This comment registers the test before any build code for it exists or merges. Max authorized it on 2026-09-30 (decision d658, ruled 12:38): "Yes: register today a report-only blind test of OACT provision A1 (COLA -1pt from Dec 2027), 2030 cost effect, vs OACT and PWBM, with MINT5 as third comparator on the COLA row; report our ratio of means and a median beside MINT's median; FRA-68 rows secondary later. Build + independent review + post the #42 registration today." The artifact publishes regardless of outcome.

This is the first of two registration comments. This one fixes the rows, the statistics, the comparators and the rules. After the build merges, a second comment posts the registered commit's full SHA, and the run waits for that comment.

OACT is SSA's Office of the Chief Actuary. PWBM is the Penn Wharton Budget Model. MINT is SSA's Modeling Income in the Near Term model, and MINT5 is its fifth version. COLA means cost-of-living adjustment. FRA means full retirement age (OACT's texts say NRA, normal retirement age). OASI and DI are the Old-Age and Survivors Insurance and Disability Insurance trust funds; OASDI is both together. TR means the Social Security Trustees Report. PIA means primary insurance amount; AIME means average indexed monthly earnings. PSID is the Panel Study of Income Dynamics. SD means standard deviation. `EV` is the evidence folder. `DM` is the design memo `EV/trust-fund-comparisons-20260929/design.md` (SHA-256 `cbea98315857a6ae923c5ce1712c16f137cb45ff424dddd5bcfa8552527cefd1`). `LOC` is the locator file `EV/trust-fund-registration-20260930/locators.md` (SHA-256 `a5db50bcc7194820370def68022e96df283142eb3d187b2606a67eba30b5f3bc`). `S` is `EV/trust-fund-comparisons-20260929/sources`. Code citations refer to `origin/master` at `dd222b9af926c773a0f92732e2d08be507793378`, with paths under `src/populace_dynamics/` unless a path says otherwise.

**What the test checks.** It checks the model's near-term cost mechanics on a closed PSID cohort: which 2030 beneficiaries carry how many reduced COLAs, weighted by their benefit dollars. It does not estimate a 75-year actuarial balance or a depletion date for any reform (DM:443). Arithmetic on the provision text alone gets most of the answer (DM:287). A match is therefore weak evidence, and the spec-only null below appears beside every comparison.

### Rows and effective dates

| Sub-row | Reform | First reduced COLA | Model fields | Year | Comparators |
|---|---|---|---|---|---|
| A-COLA (cost) | OACT A1, 2026 TR: "Starting December 2027, reduce the annual COLA by 1 percentage point" (DM:250; LOC 2.1) | the increase determined in 2027, effective December 2027, first paid January 2028 | `first_reduced_determination_year = 2027`, `annual_reduction = 0.01` (`COLAReform`, `scenario_benefits.py:394-407`; December timing per 42 USC 415(i)(2)(A)(ii), `scenario_benefits.py:20-24`) | calendar 2030 | OACT, PWBM |
| A-COLA/MINT5 (benefits by age) | MINT5's one-point COLA cut, from the start its index lists as "Start 2011" (LOC §1) | the increase determined in 2011, effective December 2011 (alternative M1: determined in 2010) | the same fields, with 2011 (M1: 2010) | calendar 2030 | MINT5 |

- **Payment timing.** Under the model's annual convention, the amount paid in year t reflects the increases determined through t − 1 (`scenario_benefits.py:66-71`). Calendar-2030 payments therefore carry the reduced increases determined in 2027, 2028 and 2029 on the cost row. On the MINT5 sub-row they carry those determined in 2011 through 2029 (2010 through 2029 on M1).
- **MINT5 runs its own reform.** MINT5 scored a one-point cut from 2011, not A1, so the MINT5 sub-row runs MINT's start date and compares like with like. The MINT5 sub-row is not a comparison of A1 with MINT.
- **FRA-68 rows come later.** OACT C1.1 ("Starting with those age 62 in 2027, increase NRA 1 month every 2 years until NRA reaches 68", run098) and C1.2 ("Increase NRA 2 months per year for those age 62 in 2027-2032", run099) are not registered here (DM:251-252). A separate, later comment on this issue registers them before any FRA build code merges. That comment will name their PWBM and MINT comparators, any CBO row, and one reading of C1.1's "1 month every 2 years" for the 2027–2030 cohorts (DM:256). This comment fixes nothing about the FRA rows. Their sources still go on the restricted list now (LOC 5.1).
- **Excluded comparators.** CBO has no one-point COLA option (DM:265), so CBO does not enter this registration. Cato is not a comparator (Max, noted on d658).

### Benefit mechanism

- **Primary: mechanism L.** L is Track A v1's legacy calculators (`cola_track_a`), and it is the only mechanism with committed real-data runs (DM:244). At `dd222b9`, `runs/` holds the exercise-1 and exercise-3 artifacts (`runs/replication_urban2010_cola_v1.json`, `runs/replication_urban2010_fra68_v1.json`) and no Track A v2 artifact. In Track A v2's terms, L computes DI levels with `legacy_fixed_35` (`track_a_v2/benefits.py:86-94`). Every AIME divides by 35 years (`cola_track_a/benefits.py:68-78`). The DI level is the disclosed oracle approximation of ruling d074 (`cola_track_a/config.py:279`).
- **Secondary: mechanism D.** D is v2's statutory DI computation (`statutory_415_b_2`, `track_a_v2/benefits.py:90-94`), with every other field of the primary cost row. D runs once Track A v2's own real-data run artifact is committed to master. It runs at a commit that a further comment on this issue registers before D runs, and the same no-drop rule covers it. If D runs after the primary comparison is posted, its output carries the label "registered before the comparator was public, run after it".

### Population, draws and conventions (both sub-rows unless stated)

- **Population.** R0's population: the PSID 2011 anchor wave, opening year 2010, born 1980 or earlier, weighted by the 2011-wave weight (`cola_track_a/config.py:128-167`). The cohort is closed. No births are drawn, everyone aged 50 or older in 2030 was alive in 2010 (`cola_track_a/adapters.py:19-22`), and no post-2010 earnings are drawn (`cola_track_a/adapters.py:25-27`).
- **Draws.** K = 20, with root seeds 5200 + k (`cola_track_a/config.py:259, 401`). Within a draw, the baseline and the reform are computed from the same projected state, with fixed paths (`cola_track_a/benefits.py:3-6`).
- **Exposure clock.** The eligibility clock: the year the worker attains 62, the year the period of disability began, or the year of death before eligibility. Auxiliaries follow the worker's clock (`cola_track_a/config.py:215`; `scenario_benefits.py:25-37, 205-222`).
- **Benefit period.** Calendar-year payments on the annual scale, 12 times the monthly amount (`cola_track_a/config.py:203, 216`; `cola_track_a/benefits.py:13-14`).
- **Components.** R0's five: retired worker, disabled worker, spouse, aged widow(er) and disabled widow(er) (`estimates/cola_age_profile.py:271-278`).
- **Baseline COLA path.** The realized series runs through 2007. TR 2008 intermediate rates apply from 2008: Table V.C1 through 2017, then the ultimate CPI. The path extends to 2030 (`cola_track_a/runner.py:231-258`; `cola_track_a/config.py:265-268, 278, 380-385`). The path stops at 2030, so 2030 is the only year this test can read (DM:242).
- **Negative reformed increases.** The `REFUSE` policy stays (`scenario_benefits.py:238-244, 407`). A refusal is reported on this issue.
- **Opening stock.** The benefit basis is frozen at the opening year (d075; `cola_track_a/config.py:245-247`).
- **Labels.** Every output carries "PSID-seeded closed cohort", "Python oracle (not Axiom)" and "fixed-path mechanical incidence" (`cola_track_a/config.py:64-69`), plus "report-only".

### Metric for the cost row

For each draw and scenario s ∈ {base, reform}:

T_s = Σ_{i ∈ S_s} w_i · b_{s,i}

P = 100 × (T_reform − T_base) / T_base

- **S_s** is every person alive in the 2030 projected state with a positive benefit in scenario s (the `positive_benefit` rule, `estimates/cola_age_profile.py:214-220`), at every age in the cohort.
- **b** is annual calendar-2030 payments summed over R0's five components.
- **w** is the person's R0 weight.
- **Equivalence.** P is the ratio of weighted totals. It uses the arithmetic of v2's `ratio_of_all_alive_weighted_totals` (`track_a_v2/estimands.py:107-133`), applied to a single all-ages cell. The new config computes P in its own module.
- **Reported value.** The run reports the mean of P over the 20 draws and the sample SD over draws (ddof = 1). It also reports the Monte Carlo floor, computed by the A7 convention (`estimates/cola_age_profile.py:96-120, 1651-1677`). For each seed 0–4, the opening-wave family units split into two disjoint halves. The reported value is recomputed on each half, and the floor summarizes |side a − side b| (mean, SD, minimum, maximum, count). An undefined floor is reported as undefined, never as zero.
- **Ratio of means.** Beside P, the run reports the weighted ratio of scenario means (`ratio_of_scenario_means`, `estimates/cola_age_profile.py:203-206`) on the same all-ages cell (d658: "report our ratio of means"). The two statistics coincide when S_base and S_reform are the same set. The run reports the count and weight of each set, so any difference shows.
- **OASI and DI split.**
  - P_DI covers the disabled-worker component. P_OASI covers the other four: retired worker, spouse, aged widow(er) and disabled widow(er).
  - Each is 100 × (ΔT) / T_base within its group, and the run reports each group's share of T_base. Per-component reform totals are new code (DM:240).
  - The component rule places a spouse's benefit that rests on an entitled, unconverted disabled worker in OASI, although DI pays it in law (`cola_track_a/benefits.py:52-57`). The run reports the weighted count and the dollars of such spouse benefits, so the size of that misassignment shows.
  - A comparator's split enters the comparison only where its sealed file prints 2030 OASI and DI cost separately. The lane records whether it does, without values.

### Metric for the MINT5 sub-row

- **Population.** MINT's Table 1 population is current-law beneficiaries aged 62 and older in 2030 (LOC 2.3). Ours is the members of S_base aged 62 or older in 2030. Age is 2030 − birth year, the code's default rule (`estimates/cola_age_profile.py:251-252, 440`).
- **Bands.** MINT's: Total (62 and older), 62–69, 70–79, 80–89 and 90+. The run re-tabulates the person-level rows into these bands.
- **Statistics.** The run computes each of the following per band and per draw, then reports the mean over the 20 draws, the draw SD and the floor, as for P.
  1. **Ratio of means** (d658): `ratio_of_scenario_means` on the band.
  2. **Median of individual percent changes.**
     - Population: the persons in S_alt within the band, meaning people who receive a benefit in both scenarios with b_base > 0 (`estimates/cola_age_profile.py:232-234`). Each person's benefit is the sum of their components, which matches MINT's "individual benefits".
     - Change: x_i = 100 × (b_reform,i / b_base,i − 1).
     - Median: sort x ascending and let W = Σ w_i. The weighted median is the smallest x_(j) whose cumulative weight reaches W/2. If the cumulative weight at x_(j) equals W/2 exactly, the median is the midpoint of x_(j) and x_(j+1).
  3. **Difference of medians.** 100 × (m_reform / m_base − 1), where m_s is the weighted median of b_{s,i} over S_s within the band, by the same rule.
- **Which median is compared.** Before the seal closes, the lane records from MINT's column heads and notes, without values, whether "Median Difference vs Scheduled" is a median of individual differences or a difference of medians (LOC 2.3). The matching statistic is the headline comparison, and the other is reported beside it. If the notes do not settle the question, the run compares both and neither is the headline. The ratio of means appears beside either one. Because the run computes the median directly, this comment registers no mean-to-median bias direction.
- **Memo items.**
  - Beside MINT's "% of Population Affected": our weighted share of the band's baseline beneficiaries whose benefit falls.
  - Our weighted median baseline and reform annual benefits. These are not compared with MINT's dollar levels, because the dollar and benefit-period bases differ.

### Registered rows

Each alternative changes one field from its primary. The one shot computes every row, and every row is published.

| ID | Sub-row | Field changed | Value |
|---|---|---|---|
| C0 | cost | none | primary, as above |
| C1 | cost | benefit period | the December 2030 monthly amount × 12 (`BenefitPeriod.DECEMBER`, which includes the increase effective December 2030; `scenario_benefits.py:247-255`) |
| C0-D | cost | mechanism | D (secondary; runs later, as above) |
| M0 | MINT5 | none | primary, with the first reduced increase determined in 2011 |
| M1 | MINT5 | first reduced increase | determined in 2010 |
| M2 | MINT5 | benefit period | the December 2030 monthly amount × 12 |
| M3 | MINT5 | exposure clock | entitlement (R2's field; LOC 2.3 (e)) |
| M4 | MINT5 | age rule | completed age at the start of 2030, 2030 − birth year − 1 (`estimates/cola_age_profile.py:247-257`) |

- **Why C1.** C0 counts the increases determined through 2029, and C1 counts those through 2030. So C0 and C1 bracket either way a comparator might time its 2030 cost. The lane records whether each comparator counts December 2030 benefits at the December 2030 increase.
- **Why M1.** The index's "Start 2011" could mean the increase effective December 2011 (M0) or the first payments in 2011 (M1). This comment fixes M0 as primary now. The lane records its reading from MINT's notes, and a mismatch is reported, never used to swap rows.

### Spec-only null

N = 100 × [ Π_{k = 2027}^{2029} (1 + c_k − 0.01) / (1 + c_k) − 1 ]

- **Inputs.** c_k is the TR 2026 intermediate COLA effective in December of year k. The null applies it to every 2030 beneficiary, as if everyone had become eligible before 2028. The memo's arithmetic puts N near a 3 percent cut (DM:287).
- **Locator for c_k.**
  - Primary: the 2026 Trustees Report's Table V.C1, intermediate assumptions, the increases effective December 2027, 2028 and 2029. That table number is the one TR 2008's COLA path comes from (`cola_track_a/runner.py:253-256`). Its 2026 counterpart has not been checked this session.
  - Fallback: if the table does not print those years, the builder uses the 2026 Report's intermediate annual CPI assumption for the same years (42 USC 415(i) ties the COLA to the CPI) and says so.
  - The builder reads only that table, not the Report's cost tables.
- **N_model (memo item).** The same formula with the model's own TR 2008 rates for 2027–2029 (`cola_track_a/runner.py:231-258`). P − N_model is the model's composition content: the share of 2030 dollars held by people who became eligible in 2028–2030, and the DI and survivor COLA clocks. N − N_model is the COLA-vintage delta.
- **N_MINT (the MINT5 sub-row's null).** The same formula over k = 2011 through 2029 (M1: 2010 through 2029), with the model's TR 2008 rates, which are also MINT5's vintage.
- **When the nulls are posted.** All three nulls are arithmetic on the specification alone. The build computes them, and the second registration comment posts their values before the run.
- **What is reported.** For each comparator C, the run reports P − C and N − C, as intervals when C is an interval, plus P − N and P − N_model. The MINT5 sub-row reports the same with N_MINT.
- **Reading (DM:287).** Agreement would show that the engine's composition and COLA mechanics are consistent with the comparator's. It would not validate long-run dynamics. A miss larger than the null's would be informative, as either a bug or a composition error.

### Year

Calendar 2030 only (DM:242).

### Comparators: locators, precision, interval rules and unit conversions

**OACT A1, 2026 TR basis** (LOC 2.1)
- **Page.** `https://www.ssa.gov/oact/solvency/provisions/tables/table_run113.html` (PDF twin: `.../tables/table_run113.pdf`), in the current `provisions/` folder, where category A is on the 2026 TR basis. The comparator is not `provisions_tr2025/tables/table_run113.html`. In the 2025 folder, run113 is B1.3, because run numbers collide across folders (DM:197).
- **Footer vintage (required).** "Based on Intermediate Assumptions of the 2026 Trustees Report". If the footer differs at fetch time, the lane stops and reports. It does not substitute another page. The sealed copy is the comparator.
- **Text to match.** "Starting December 2027, reduce the annual COLA by 1 percentage point."
- **Cells.** Table 1, the single-year table, calendar-year row 2030. From the "Proposal" column, the cost rate p. From the "Change from current law" column, the cost rate d. The lane records the header strings verbatim. The proposal income rate and the change in income rate are memo items.
- **Unit.** Percent of current-law taxable payroll.
- **Published precision.** Two decimals. The format was checked on run115, a page of the same family (DM:268). The lane confirms the format on run113 without reading values.
- **Conversion.** The current-law cost rate is CL = p − d, and C_OACT = 100 × d / (p − d) (DM:261). Payroll cancels.
- **Interval rule.** p and d each carry ±0.005, so the derived CL carries ±0.01. The C interval runs from the minimum to the maximum of 100 · d / (p − d) over the four corners (p̂ ± 0.005, d̂ ± 0.005). The corners suffice because, while p − d > 0, C is monotone in d and, for fixed d, monotone in p.
- **Precision gate (DM:268).** If any OACT column that enters the statistic is smaller than 0.10 in magnitude, PWBM becomes primary and OACT report-only. Under d658 both are report-only already. The lane still applies the gate mechanically and records which branch applied.

**PWBM `cola_offset_cut_1pp`** (LOC 2.2)
- **Pinned folder.** `https://pwbm-website-data.s3.us-east-1.amazonaws.com/social-security/2026-09-20-marikop-upload/` (DM:197).
- **Slug.** `cola_offset_cut_1pp` is A1: "Starting December 2027, reduce the annual COLA by 1 percentage point". Its source is table_run113 on the 2026 TR basis (`S/pwbm-social-security.md:30-31`, as LOC records).
- **File.** `{folder}/cola_offset_cut_1pp/law_change/law_change_brief/charts/cost_and_income_rate.csv`. On 2026-09-30, a HEAD request returned HTTP 200 with `Last-Modified: Tue, 22 Sep 2026 20:43:15 GMT`. The seal pins the bytes it fetches. A later change to the object is reported, not substituted.
- **Header.** `year,Baseline income rate,Baseline cost rate,A1 income rate,A1 cost rate`, preceded by a UTF-8 byte-order mark.
- **Cells.** Row `year` = 2030. B = `Baseline cost rate` and R = `A1 cost rate`. Both income-rate columns are memo items.
- **Unit.** Percent of PWBM's own baseline taxable payroll.
- **Conversion.** C_PWBM = 100 × (R − B) / B (DM:262).
- **Published precision.** Full precision: 15 decimals, checked on a different slug's file (DM:268). The lane counts the stored decimals of B and R in the 2030 row without printing them.
- **Interval rule.** If both stored values carry six or more decimals, C is a point value. Otherwise B and R each carry ± half their last stored unit, and C runs over the four corners, as for OACT.
- **Also recorded (specifications, no values).** The lane records the "Divergence(s) from the policy scored by SSA" text in `law_change_brief.md` and PWBM's definition of cost. The brief's Table 2 is restricted.

**MINT5, archived Office of Retirement Policy table** (LOC 2.3)
- **Original URL.** `http://ssa.gov/retirementpolicy/projections/colas/reduce-COLA-by-1-point-2030.html`. The live tree now returns 404.
- **Archive capture.** `https://web.archive.org/web/20111030080836id_/http://ssa.gov/retirementpolicy/projections/colas/reduce-COLA-by-1-point-2030.html`, CDX digest `HQABASP6M6XNNB4FM6R4PC3JDJLHEJJ3`.
- **Twins in the same capture set.** `...-2030.xlsx` at `web/20111030094220id_/`, digest `4M3YURYZAVDWU6KTJ34FT5GMAIBIMOX3`; `...-2030.pdf` at `web/20111030094225id_/`, digest `XOEMLRJGQZWRMM5XBX5QNHMZG7PREHOG`.
- **Text to match.** The source line "SSA's Office of Retirement Policy, using MINT 5/ TR 08 Assumptions/ SSMBA 3.1. Run: 08/12/2011" and the title "Reduce the Cost of Living Adjustment by 1 percentage point, 2030".
- **Cells.** Table 1, "Overall individual benefits 2030". The rows are Total, 62-69, 70-79, 80-89 and 90+. The column is "Median Difference vs Scheduled", "%" sub-column. Memo items: its "$" sub-column, "Median Monthly Benefit" (Scheduled and Option, with Payable as a reference), "% of Population Affected", and Table 2, "Affected individual benefits".
- **Unit and conversion.** Percent against scheduled benefits. Ours is computed in the same unit, so no conversion applies.
- **Published precision.** Not yet recorded, because the research lane masked every numeral. Without printing values, the lane records the displayed decimals of the HTML "%" column and the stored decimals in the XLSX twin.
- **Interval rule.** If the XLSX stores more decimals than the HTML displays, and the stored value rounds to the displayed one, the XLSX value is the registered point, ± half its last stored unit. Otherwise the HTML display is registered, ± half its last displayed unit.
- **Vintage.** TR 2008 intermediate, the same as the model's. MINT5's table is static.

**Comparator lane.** A fresh validation-only lane fetches and seals the comparators. It is neither the research lane nor the memo's reviewer or reviser.
- Two transcribers work independently, and their results are reconciled.
- The lane seals them in `EV/acola-comparator-seal-20260930.json`. The seal holds the SHA-256 of every fetched file, the retrieval dates, the OACT footer string, the PWBM folder and `Last-Modified`, and the MINT capture timestamp and digest (LOC 3).
- It runs a values scan on anything builders will read (DM:195).
- The seal opens only after the run artifact merges.

### Adjustments

No adjustment changes any number. Each difference below is named on the output with its source.

- **Cost definition (dilution).** The TR 2026 glossary defines cost as scheduled benefits plus administrative expenses, the financial interchange with the Railroad Retirement program and vocational rehabilitation payments (DM:269). Administrative expenses do not change with the reform, so the comparators' percent is slightly diluted relative to a benefits-only P. The Railroad Retirement interchange may move with a benefit change, and the sources do not say in which direction. The lane records PWBM's cost definition, and where a source is silent, its dilution is registered as unsigned.
- **Closed cohort versus full population (context only).** The model has nobody under 50 in 2030 and no post-2010 immigrants (DM:270). Every beneficiary type gets the reduced COLAs, so the missing groups dilute the COLA row little (DM:271). The output sets the model's weighted 2030 beneficiary count beside the all-ages 2030 OASDI count in the committed TR 2026 snapshot `data/external/snapshots/ssa_level_anchors_vintage1/trustees2026_lr4b4.html` (DM:270), as context only. The row is not scaled; the scaling by the share of benefit dollars going to people 50 and over applies only to the FRA rows (DM:272).
- **Scheduled versus payable.** 2030 comes before depletion in both TR 2026 and PWBM's baseline (DM:273). Every comparison is on scheduled benefits, and MINT's column is "vs Scheduled".
- **Baseline vintage.** The model uses TR 2008 paths. OACT uses TR 2026, PWBM its own baseline, and MINT5 TR 2008 (DM:274; LOC 2.3). The percent metric removes most level differences, because a one-point cut scales benefits by about (1 + c − 0.01)/(1 + c) per reduced COLA and so depends only weakly on the COLA c (DM:274). The vintage is named as a delta, and N − N_model measures its COLA-rate part.
- **DI and auxiliaries.** Children are absent. Disabled widow(er)s appear only in the opening stock and are not projected (DM:275; the projected components are listed in `cola_track_a/benefits.py:38-62`). This is minor for the COLA row.
- **COLA timing.** C0 and C1 bracket the comparators' timing, as described under "Why C1". No adjustment applies.
- **Taxation of benefits.** The test compares cost only, not annual balance, which nets the change in income. OACT's and PWBM's income-rate changes are recorded as memo items; they feed Option B (DM:276).

### Pass criteria

The test is report-only. No pass band exists, and nobody set one (d658; DM §5, question 2). Track A carries no numerical acceptance threshold (d074), and `TrackAConfig` refuses an acceptance rule (`cola_track_a/config.py:386-390`). The new config carries no acceptance rule either. No band may be added after this comment. For each comparator, the output reports the model's value (mean, draw SD and floor), the comparator's interval, the gap interval and the null's gap.

### Predicted bias directions, registered in advance

From the memo (DM:278-285), the items that apply to the COLA row:
- **No earnings after 2010.** Cohorts reaching 62 in 2027–2030 have AIMEs built on careers that stop at ages 42–45, so their PIAs are understated and their share of 2030 benefit dollars is too small. The 2028–2030 cohorts carry fewer reduced COLAs (the 2027 cohort carries all three), so this pushes the model's COLA effect slightly away from zero (DM:279).
- **Net.** The COLA row is primary. The FRA biases, which mostly push away from zero, belong to the later FRA registration (DM:285).

Added by this drafter, deduced from code read this session and labelled as deductions:
- **Claiming vintage.** Claiming snaps to the 2008 claiming table (`cola_track_a/config.py:272-274`). If early claiming has fallen since 2008, which this session did not check, the model has too many beneficiaries aged 62–64 in 2030. On the eligibility clock, those people became eligible in 2028–2030 and carry at most two reduced increases in 2030 payments. This pushes the COLA effect slightly toward zero.
- **COLA-rate vintage.** The per-COLA factor 1 − 0.01/(1 + c) rises with c. So if the model's TR 2008 rates exceed TR 2026's for 2027–2029, the model's cut is slightly smaller in magnitude, and the reverse also holds. The sign of N − N_model, posted before the run, fixes this direction.
- **Timing.** If a comparator counts December 2030 at the reduced December 2030 increase, C0 lies slightly closer to zero than that comparator, and C1 bounds the gap.
- **MINT5 sub-row (M0–M4).** Added after the independent review, deduced the same way. The claiming-vintage item applies: in 2030, people aged 62–64 carry at most two reduced increases under M0 and M1, so too many early claimants pull the 62–69 band and the total toward zero. The COLA-rate-vintage item does not apply, because MINT5 and the model both run on TR 2008. The no-earnings item moves the ratio of means mainly through benefit-dollar weights, and moves the median of individual percent changes little.

This comment registers no candid forecast; d658 does not call for one. The nulls, posted before the run, are the stated expectation.

### Rules

- **One shot.** The run happens once, at the registered commit. There is no tuning and no rerun. Any code or specification change after the second comment needs a new registration.
- **Re-execution.** One disclosed re-execution is allowed, and only for an external infrastructure failure before any value is scored. It is reported here before relaunch.
- **No-drop rule.** The one run computes every row, alternative, statistic, memo item and null listed in this comment, and all of them are published, including any undefined value with its reason. Nothing is dropped. The secondary D row runs later under the same rule, and the FRA rows will run under their own registration's.
- **Publishes regardless.** The artifact merges by its own PR, a second review-and-CI cycle, before the seal opens (DM:215). A validation-only lane opens the seal, and the orchestrator verifies the result and posts it on this issue whatever it shows (DM:216).
- **Topology.** The run executes under launchd, detached from the desktop app, as Registrations 13–17 did. If a guard refuses the run, the refusal is reported here, as Registration 14's was.

### Build, and what the second registration comment posts

The build follows DM:289-302:
- **Separate config.** A separate config module holds its own registered-row set with the rows above. `REGISTERED_ROWS` (`cola_track_a/config.py:225-241`), the exercise-1 and exercise-3 constants and `_check_reform` (`fra68_track/reform.py:377-411`) stay unchanged. Track A v2 imports `REGISTERED_ROWS` (`track_a_v2/matrix.py:8`) and the v1 and FRA runners (`track_a_v2/runner.py:20-31`), and `scripts/track_a_dry_run.py:386-395` checks every registered row against the A1 block.
- **Entry script.** A thin copy of `scripts/run_track_a_registered.py` keeps its guards. The registration pointer must be a comment URL on this issue, and the run refuses unless `HEAD` equals `--registered-commit` on a clean tree (`scripts/run_track_a_registered.py:178-192`). The pointer is this comment's URL.
- **New code.** The aggregate statistic with per-component reform totals, the OASI and DI split, the MINT-band statistics, the three nulls, and a `compare.py` for the comparison lane.
- **Start-year check.** Today's rows start their reduced increases in 2009 or 2010 (`scenario_benefits.py:180`; `cola_track_a/config.py:229-230`). The build checks that nothing downstream assumes a first reduced increase at or before the 2010 opening year (DM:297).
- **Review.** Tests use invented data only. An independent review precedes the merge (d658). The build coordinates with the Track A v2 and U2 lanes before touching shared modules (DM:302).

The second registration comment, posted after the merge and before the run, gives:
- the registered commit's full 40-hex SHA and the exact run command;
- the SHA-256 of the committed specification file that restates this comment, with a statement that the file matches it;
- N, N_model, N_MINT and M1's null, with the TR 2026 file, table and row that c_k comes from, and that file's SHA-256;
- the comparator seal's SHA-256 and the lane's value-free records: OACT's header strings and footer, the stored decimals of PWBM's values, MINT's median type, age convention and decimals, MINT's start-date reading, each comparator's December 2030 timing, and whether any comparator prints an OASI and DI split.

### Blindness caveat

The blindness is procedural, not informational (DM:218).
- **Public tables.** OACT, PWBM and MINT publish these tables, and model-built code may carry training priors.
- **Mitigation.** The registered runs have no free parameters once registered, and single-year 2030 cost changes are unlikely to be memorized.
- **Limit 1: MINT5 is close to exercise 1.** The MINT5 sub-row's reform is close to exercise 1's R1 row: a first reduced increase determined in 2010, with 2030 benefits by age. That row's model result and its DYNASIM comparator have been public on this issue since 2026-09-23. The sub-row therefore tests the statistic and population definitions more than fresh mechanics.
- **Limit 2: DM prints run115 numbers.** Lines 268, 343 and 475 print numbers derived from OACT run115 (provision A3, chained CPI from December 2027); line 268 also prints CBO 2015's current-law 2030 outlays (LOC 5.3(a)). Scaled by A3's stated average COLA reduction, line 343 or 475 gives a near-linear proxy for A1's 2030 cost change. Builders do not read those lines. The restricted list adds DM. Builders work from this comment and their brief, and may follow its DM citations only in a copy with lines 268, 343 and 475 redacted, after a values scan.

### Disclosure: who has seen what

- **The research lane** behind the comparator report disclosed exposure to OACT's removed provision A7 row, CRFB's FRA-68 "gap closed" share, some CBO 2015 Option 25 and 33 sentences, and the Trustees Report's "size needed" cut (DM:198). It does not build.
- **The memo's reviewer** declared opening OACT's category pages and PWBM's exercise-slug descriptions (DM:198). It does not build.
- **The memo's reviser** read, with values, the full OACT run115 table, CBO 2015's current-law and Option 29 2030 cells, and the 2030–31 rows of PWBM's `oasdi_rate_13_4` CSV (a payroll-tax provision, whose rows may carry PWBM's baseline 2030 cost rate), as DM:9 records. It does not build.
- **The locator step** (three Claude Code workflow agents, Opus 5.5, 2026-09-30; the third wrote LOC) will not build or forecast. The second agent read DM in full, lines 9, 268, 343 and 475 included, so it saw OACT's current-law 2030 cost rate and A3's 2030 income-rate and cost-rate changes. The first and third printed DM lines 9, 268 and 475 in full and saw line 343 with decimals masked. The first agent's mask hid only the digits next to each decimal point. All three read the `S/` notes on OACT, PWBM, MINT, CBO and CRFB, and sections of the other-models note. The third also read Cato's `commands.txt` with decimals masked. The second agent downloaded the archived MINT5 2030 HTML and XLSX and PWBM's A1 cost-rate CSV, and printed only their labels, structure and stored-decimal counts. The third made the HEAD request and the 512-byte header read described in LOC lines 8–14.
- **This registration's drafter** (a Claude Code subagent, Opus 5.5, 2026-09-30) will not build or forecast.
  - **What it read:**
    - DM's heading list and lines 180–219 (the common protocol), 234–328 (Option A) and 433–471 (sections 4 and 5). It did not read lines 1–179, 220–233, 329–432 or 472–479, so it did not see lines 9, 343 or 475.
    - LOC in full.
    - `EV/RESTRICTED-FILES.md` (SHA-256 `241a6855…`) in full.
    - The repository files cited above, at `dd222b9`.
    - On this issue, it read:
      - the first line of each of the last 90 comments;
      - Registration 13 in full, including its forecast table for exercise 1;
      - the headings and bold-led lines of Registrations 14–17;
      - Registration 17's opening paragraphs, rules and drafter disclosure.

      It opened no result comment.
    - The d658 record in the decision ledger.
    - File-name listings of the trust-fund folders and of the repository tree.
  - **What it did not open:** any OACT, PWBM, MINT, CBO or CRFB page or file; any `S/` note; the other-models note; any TR 2026 page or snapshot; any comparator lane or seal; any run artifact.
  - **Exposure:** it has seen no A1 value from any comparator. Reading DM line 268 in full, it saw OACT's current-law 2030 OASDI cost rate, which the memo derives from run115 as proposal minus change, and a precision figure computed from it. That rate is a current-law baseline, not an A1 or A3 change. Current law is common to every 2026-TR provision page, so within rounding it equals the denominator p − d of C_OACT. The same line gave it CBO 2015's approximate current-law 2030 outlays as a share of GDP, a baseline for the later FRA rows. It has not seen p or d for run113, A3's 2030 changes (DM:343, 475), or any comparator's numerator. Its only network requests were GitHub API reads of this issue.
- **Review and revision lanes** (Claude Code subagents, Opus 5.5, 2026-09-30) will not build or forecast. A first round-1 review attempt printed DM line 268 in full, so it saw OACT's current-law 2030 cost rate and CBO 2015's current-law 2030 outlays. The round-1 reviewer read lines 9, 268, 343 and 475 with every digit masked. The lane that drafted the round-1 fixes read line 475 with digits masked. The round-2 reviewer saw no DM value.
- **Builders** are fresh lanes that read `RESTRICTED-FILES.md` first and open nothing it lists. The list gains this test's sources, their earlier vintages and proxies, the FRA-row sources and the lane's output paths before any builder starts (DM:199-212).
- **The orchestrating session** (Claude Code, Opus 5.5) will not build or forecast. On 2026-09-29 at 14:34 UTC, a minute after the memo's last edit, it printed DM lines 12–19, 75–93 and 433–480 in full. That range includes line 475, so it saw A3's (run115) 2030 cost-rate change, a near-linear proxy for A1's 2030 cost change. A context compaction later that day removed the read from its working record; its session transcript shows it. On 2026-09-30 it read DM's heading list and lines 180–330, with every line cut at 400 characters. On line 268 that view ends before the current-law cost rate and shows only the precision rules (±0.005 on OACT's printed columns, ±0.01 on the derived rate). It did not read DM lines 9 or 343, and it opened no comparator page or file. On 2026-09-29 it coordinated the comparator research lane and worked from that lane's notes (the other-models note and specs-only notes under `S/`), so it cannot rule out having seen values there. Any builder brief it writes passes the values scan (DM:195) before a builder reads it.
