# Income and resources: covered earnings, wealth and pensions, and SSI

- **Status:** draft revision 0, 21 October 2026, for review. It authorizes no build, registration, real-data run or change to any other design. Nothing in it has run.
- **Authority:** Max authorized this lane on 2026-10-21 (decision d1802). Its first deliverable is this priced design; building waits for his approval of it.
- **Scope:** three rows of `docs/parity-ledger.md` at master `1e739d32`: *Covered earnings and agreement with SSA records*; *Wealth, pensions and other income*; *Supplemental Security Income (SSI)*.
- **Format:** modelled on revision 3 of the Track B design (`~/microcosm-launch-evidence/dynasim-parity-20260909/trackb-design-20260928.md`, approved under d515): its milestone table (§3.1), verification classes (§3.2), admission rules (§5), risks and kill criteria (§7) and staffing assumptions (§8).

**Every effort figure in this document is an estimate.** The figures are engineering judgments under the staffing assumptions in §11, not demonstrated throughput. "d" means engineer-days and "lw" means agent-lane weeks at 4 engineer-days a week; in every cell lw = d ÷ 4 exactly.

Abbreviations: SS is Social Security; SSI is Supplemental Security Income; PE-US is PolicyEngine-US; FBR is SSI's federal benefit rate; ABD is aged, blind or disabled; DB and DC are defined-benefit and defined-contribution pensions; IRA is an individual retirement account; RET is the retirement earnings test; EPUF is SSA's 2006 Earnings Public-Use File; SCF and SIPP are the Survey of Consumer Finances and the Survey of Income and Program Participation; MINT is SSA's Modeling Income in the Near Term model. `EV` is `~/microcosm-launch-evidence/dynasim-parity-20260909`.

## 1. Purpose

DYNASIM projects, for each simulated person, the income a reform changes: Social Security, but also the pensions, retirement accounts, asset income and SSI that sit beside it. The parity ledger lists those as three missing capabilities (`docs/parity-ledger.md:90, 129, 130`). This design prices the work that would make each one testable, and then comparable with DYNASIM's and MINT's published income tables.

It follows Track B's rules (Track B §1, §5.1):

- Each mechanism, population and horizon is admitted separately, and only through a registered gate against independent observations.
- No DYNASIM or MINT comparison may select structure, parameters, denominators or rows. Agreement with DYNASIM or MINT never rescues a failed gate.
- Source hashes, populations, estimands, tolerances and alternatives are frozen before any real-data outcome is computed.
- Every milestone reports its verification class and admitted scope (§4.2).

Two facts shape the plan. First, all three rows can be gated on PSID and SSA data now, without waiting for Track B's forward-earnings successor (d1659): their gates score histories and held-out waves the PSID already holds. Second, none of them can enter a 2030 projection, or a comparison with DYNASIM or MINT, until Track B's chain (H, B4, J, B7) and a representative starting population exist. The milestones are ordered so that the first fact is used and the second is respected.

## 2. What exists now

Every citation in this section was read in this run at master `1e739d32`, unless it names another revision.

### 2.1 Covered earnings

- **No split exists.** The projections and the Axiom bridge treat all PSID labor income as covered (`docs/parity-ledger.md:90`).
- **A correction design exists, and stopped.** `docs/design/covered_earnings_correction.md` is 56,304 lines (4.0 MB): a base design in §§1–14 and nineteen appended amendments in §§15–33. Its charter classifies each person-year source component as `covered_wage`, `covered_self_employment`, `noncovered` or `unresolved` (§1, lines 30–34), with a frozen statutory ordering in which wages consume the taxable maximum first and self-employment only the remainder (§3.2, lines 286–321). Amendment 1 removed a required SSA covered-share target that no publication supplies (§15.2, lines 8185–8199). Amendment 2 added a deterministic, fitting-free correction path (§16.1, lines 9193–9220). Issue #403 records a law-gap sweep at revision 21 that found nine further seams. PR #405, Amendment 20, closed unmerged on 25 September 2026, and the ledger records that the campaign stopped on 9 September.
- **Pieces of it are code.** `src/populace_dynamics/data/historical_coverage_rule_validation.py` validates the syntax of legal-rule rows and defers everything that needs a ratified inventory (lines 1–9). `src/populace_dynamics/data/psid_covered_earnings_registry.py` freezes the PSID reference-year map and exposes a fail-closed boundary instead of an official crosswalk (lines 1–11). `src/populace_dynamics/covered_wage_history.py` attaches declared covered-wage observations to a history and "never infers wages from labor income" (lines 1–6).
- **The PSID job context is read for 2003–2023 only.** `src/populace_dynamics/data/psid_job_context.py` emits raw, uninterpreted tokens (lines 1–8) for occupation, industry, self-employment, incorporation, the government-employer item (`BC24`/`DE24 WORK FOR GOVT?`) and state, for interview waves 2003–2023 (`psid_job_context_registry.py:33, 270–320`). No value code of the government item has been adjudicated.
- **SSA's earnings file is staged.** `src/populace_dynamics/data/epuf.py` reads the 2006 EPUF, a 1 percent sample of SSNs with capped taxable earnings, covered wages plus covered self-employment, for 1951–2006, byte-pinned (lines 1–43). `gate_epuf` closed without locking and has scored no model output (`docs/parity-ledger.md:90`); `gate_epuf_fill` used EPUF to certify career fills (`:89`).

### 2.2 Wealth, pensions and other income

- **Reported wealth, waves 2005–2013.** `src/populace_dynamics/data/family_income.py` reads label-verified family income and WEALTH1 for the 2005, 2007, 2009, 2011 and 2013 waves (lines 1–30). From 2009 the family file carries the wealth composites; for 2005 and 2007 it reads the PSID wealth supplements, which Max downloaded and staged under decision d189 (lines 52–77). Only those two supplements are staged (`~/PolicyEngine/psid-data/wealth/`: 2005, 2007). The PSID family files for every wave from 1968 to 2023 are staged (`~/PolicyEngine/psid-data/family/`).
- **Employer DC balances, waves 2005–2013.** `src/populace_dynamics/data/employer_dc.py` reads the pension section's current-job and previous-employer account balances for head and wife, following the questionnaires' routing item by item (lines 1–110). It also documents the section's plan-type items (DB formula, DC account, both) and the expected-benefit item `P62`.
- **One static use.** Exercise 2 annuitizes 80 percent of WEALTH1 (optionally plus employer DC balances) into a level real annuity at 3 percent, priced on the NCHS 2000 life tables, joint and 50 percent survivor on the family head and spouse (`src/populace_dynamics/estimates/adjusted_poverty.py:49–70, 404–426, 851–912, 1340–1397, 1553–1559`). It replaces reported asset income with that annuity (`:22–38, 1560–1573`).
- **Microcosm's frame carries wealth and pension income, but not every piece.** The Microcosm-start plan maps the frame's variables (`docs/plans/microcosm-start.md:269–284`): household `net_worth` from a QRF anchored on the SCF 2022; liquid assets (`bank_account_assets`, `stock_assets`, `bond_assets`) on the household head; DB pension income from the 2015 IRS file; retirement-account withdrawals; asset income. It has **no employer DC balance, no DB coverage and no home value** (`:282`).
- **A first ageing rule is proposed, not built.** The same plan's §2.3 (lines 286–302) ages each income and wealth item by keeping each unit's rank within its sex, age-band and household-type cell, with a report-only check, A1, against the PSID's wealth panels. Its tasks T3 (PSID wealth readers for 1999–2021, 4–6 agent-days) and T10 (the table, the rule and A1, 6–10) are priced there (`:414, 421`). The plan's registration waits on d947, which is parked.
- **A Form 5500 reader is in review.** PR #386 (open, last updated 24 August 2026) adds readers for DOL Form 5500 plan-sponsor filings and OSHA establishment summaries. It is unmerged.
- **Nothing projects wealth, pensions or asset income** (`docs/parity-ledger.md:130`).

### 2.3 SSI

- **A static offset.** Exercise 2's primary rule raises each baseline SSI recipient's SSI by the fall in countable Social Security income after the $20 general exclusion, capped so SSI stays at or below the FBR, and enrolls no one (`adjusted_poverty.py:96–106, 1420–1449`; Max's ruling d189). A registered alternative also enrolls head/wife units the cut makes income-eligible and whose WEALTH1 less vehicles passes the resource limit (`:1450–1475`). Federal SSI only; its parameters are a pinned capture from PE-US (`:199–204, 1085–1122`).
- **Registration 19.** `docs/design/pe_us_depletion_cut_population.md` (ratified `sa1-ratified-1`) ran PE-US 2.18.0's SSI on Microcosm's 2024 frame, static and report-only, with imputed liquid assets (§§1–2) and code merged in #511 (`src/populace_dynamics/bridge/depletion_cut_population*.py`). Its §4 reads PE-US's SSI encoding: countable resources are exactly bank, stock and bond assets; the $2,000 and $3,000 limits are not indexed; 2.18.0 deems an ineligible spouse's and parent's income but not their resources; and its spousal-deeming cap differs from 20 CFR 416.1163(e)(2) (§4.1, §12 items 3 and 12).
- **The bridge's person inputs are narrow.** `src/populace_dynamics/bridge/policyengine_us.py` passes Social Security by type, employment income, taxable private pension income, interest income, bank-account assets and rent (`:225–236, 278–291`). It passes no stock or bond assets, no disability or blindness status and no retirement-account balance. It runs PE-US in a separate interpreter, pinned by default to 2.18.0 (`:128–132`), and accepts parameter overrides per run (`RunCase.parameter_overrides`, `:810–818`).
- **Nothing projects SSI.** The engine's eight modules include no SSI step (`docs/parity-ledger.md:108`; `src/populace_dynamics/engine/loop.py`).

### 2.4 PolicyEngine-US and Axiom, checked in this run

- **PE-US 2.18.0** (the bridge's pin; installed at `~/.venvs/policyengine-us-2.18.0`) has federal SSI with income deeming from an ineligible spouse and parent, in-kind support and maintenance, living arrangements including the one-third reduction, and couple computation (`variables/gov/ssa/ssi/`, `ssi_amount_if_eligible.py`). Files whose names contain `state_supplement` exist for nine states (AK, CA, CO, IN, KS, MA, NM, SC, TX); other states' supplements, if encoded, use other names, and SSI2 inventories them.
- **PE-US 2.53.1**, the latest release on PyPI on 21 October 2026 (wheel SHA-256 `fc5cd5c4…d8d8`), adds resource deeming from an ineligible spouse and parent (`variables/gov/ssa/ssi/eligibility/resources/deemed/`). Its countable-resource list is unchanged: bank, stock and bond assets only, with the note "Excludes home, one vehicle, household goods, burial plots, and retirement accounts" (`parameters/gov/ssa/ssi/eligibility/resources/countable.yaml`).
- **That exclusion departs from SSA's rule for the claimant's own accounts.** POMS SI 01120.210 (captured 2026-10-21, SHA-256 `9dd41ec4…fc4e41`) says a retirement fund owned by an eligible individual "is a resource if he/she has the option of withdrawing a lump sum," valued at what can be withdrawn after any early-withdrawal penalty; it is not a resource if the person must leave the job to get it; and an ineligible spouse's or parent's retirement fund is excluded from deeming (§§A.3, B, C.1, E.4). A projection that carries IRA and DC balances therefore needs the rule PE-US lacks.
- **Axiom.** `rulespec-us` at origin/main `5796861e5` (20 October 2026) encodes parts of the SSI statute: 42 U.S.C. 1382(a)(1)–(3), 1382(b), 1382(e)(1), 1382a(b)(2), 1382a(b)(4), 1382b(a), 1382c(a)(1)–(2), 1382f(a) and 1382f(c). It encodes no 20 CFR part 416 regulation. Differential checks against it are possible for those sections only.
- **PolicyEngine's interface rule.** PolicyEngine's guidelines make policyengine.py the user-facing interface and PE-US a transitional adapter, with every PE-US policy fix mirrored in rulespec-us in the same piece of work (`~/PolicyEngine/CLAUDE.md`). SSI0 (§4.1) chooses between the existing subprocess bridge and policyengine.py under that rule.

### 2.5 Legal facts the design relies on, checked in this run

- **The RET counts noncovered wages.** 42 U.S.C. 403(f)(5)(C) deems services that are not covered employment, performed in the United States as an employee, to be employment for the earnings test, and excludes from wages any payment "on account of retirement" (Cornell LII capture, SHA-256 `089ec01f…df41a`). So earnings-test earnings are not covered earnings, and pension income does not count toward the test.
- **The windfall elimination provision and the government pension offset are repealed** for benefits payable for months after December 2023 (Public Law 118-273, approved 5 January 2025; govinfo capture SHA-256 `98eedeab…ad72`). Noncovered pensions no longer reduce projected benefits; they still mattered for benefits paid before 2024.
- **SSI's benefit rates are indexed and its resource limits are not.** 42 U.S.C. 1382f(a) raises the FBR amounts by the Social Security COLA, applied to the unrounded prior amount and rounded to the next lower multiple of $12 a year (LII capture, SHA-256 `58078380…8388`). It indexes the benefit-rate subsections of §1382 and not the resource limit.

The captures sit in `EV/income-resources-20261021/sources/` with their hashes.

### 2.6 What the coordinator priced

The coordinator's forecast of 21 October (`EV/coordinator/parity-forecast-20261021.md:98–100`) lists, as its own order-of-magnitude estimates, covered earnings at 8–12 engineer-days, SSI in the projection at 10–20 and wealth, pensions and other income at 30–60, "the largest item." No design priced them. §4.4 sets this design's figures beside those.

## 3. Design

### 3.1 Covered earnings: a lean successor to the correction campaign

**Recommendation (decision 1, §12):** retire the 56,304-line correction design as a campaign, keep its estimands, and build a short successor, CE v2.

The old design's substance is sound and is kept: the four statuses; the rule that unresolved earnings are never silently counted as covered; wage-first cap coordination, with no self-employment loss offsetting wages (§3.2 of that design); one ledger that both benefits and revenue read (§3.3); the "frame-relative" label; and Amendment 2's fitting-free path, which fits nothing to official totals. What is dropped is the ceremony that surrounds it: exact-dyadic encodings, nested ratification oracles and the amendment layers that the #403 sweep found would each cost another stop-and-cure round.

**CE v2, in four parts.**

1. **A coverage-rule registry** (CE1). Each rule has effective dates and a citation: federal civilian service (CSRS-era service not covered for OASDI; FERS-era service covered); state and local government (covered under a Section 218 agreement, or, from July 1991, when the worker is not a member of a public retirement system); railroad service; ministers and members of religious orders; students working for their school; household and agricultural workers below the statutory thresholds; and self-employment below the net-earnings floor. Each rule carries worked examples from SSA's published guidance. This is statutory conformance; it uses no PSID data.
2. **A PSID job-context crosswalk for 1968–2001** (CE2). It extends the existing 2003–2023 reader to the earlier waves and adjudicates the value codes of the government-employer, industry, occupation, self-employment and state items in every wave, with the repository's label-verification discipline.
3. **A classifier** (CE3). Where the data identify coverage, the rule decides it: a private employee is covered, a federal employee's status follows the hire-year rule, self-employment follows the threshold. Where they do not, chiefly state and local government workers, the classifier assigns a probability of noncoverage from published aggregate sources by state, occupation group and era (D4), and leaves the remainder `unresolved`. It fits nothing to the SSA totals it is later checked against.
4. **A registered gate, CE-G** (CE4). It scores PSID-corrected careers against EPUF by birth cohort, sex and age band for 1968–2006, on cells where noncoverage matters: the share of person-years with positive covered earnings, capped covered-earnings quantiles, and years without covered earnings. Its bite check must show the uncorrected proxy (all labor income covered) failing cells that CE v2 claims to fix. SSA's covered-worker and taxable-earnings totals (Annual Statistical Supplement section 4) are reported beside it, frame-relative, until a representative population exists.

**What CE v2 hands on** (CE5): one person-year table for 1968 onward with labor earnings, covered wages, covered self-employment, noncovered earnings, unresolved earnings, RET-countable earnings (covered plus noncovered wages plus net self-employment earnings, per 42 U.S.C. 403(f)(5)) and the status probabilities, with provenance. AIME uses the capped covered channels. The earnings test uses the RET-countable channel. National payroll (Registration 18, M7) uses capped covered payroll.

**Projected years.** The forward-earnings law has no job identity, so a projected year cannot be reclassified from a new job. CE v2 v1 carries each person's last observed coverage status forward, a named limitation with a registered sensitivity (status reset to "covered" at a modelled job change). A job process would be needed to do better, and none is planned.

### 3.2 Wealth and pensions: a null, a donor model and a structural option

Three model tiers, each a registered candidate, each scored by the same gate:

- **M0, the null.** The Microcosm-start plan's rank-preserving rule (§2.3 of that plan): each unit keeps its rank within its cell and takes that rank's value from the start-year cross-section as it ages. It is the baseline any candidate must beat, and its known flaw (it uses the cross-section's age profile as each cohort's future, which overstates DB pensions for younger cohorts; `microcosm-start.md:296`) is what the gate's bite check targets.
- **M1, donor trajectories (the proposed candidate).** At each projected wave, match each unit to PSID donors observed over the next two years on age, sex, marital state, household income rank, net-worth rank and pension state, and carry the donor's change in ranks and pension state. This is the same idea that passed gate 1 for earnings histories (rank-kNN; `docs/plans/microcosm-start.md:132–142`), where a QRF chain that forgot each person's history failed. The state it carries: net worth and its components (liquid assets, retirement accounts, home equity, other assets, debt); DB coverage on the current job, vesting and receipt; DC participation and balance; pension income. Events change ranks by rule: a surviving spouse keeps the household's assets, a divorce splits them by a registered rule, and a death removes them from the population as a recorded exit.
- **M2, structural accumulation (conditional; priced separately as WP7).** Explicit DC contributions within statutory limits, employer match, returns on a named assumption path, leakage at job change, and DB accrual by sector. It is built only if M1 fails its gate, or if a comparison needs saving to respond to a reform. It needs a ruled return assumption (decision 2, §12).

**The rule layer** (WP2) is statutory and shared by all three: required minimum distributions (age 73, and 75 for those born in 1960 or later, under the SECURE 2.0 Act), the 10 percent additional tax on early distributions (IRC §72(t)) that sets SSI's resource value of a withdrawable account, contribution limits (IRC §§402(g) and 415(c)), and the cost-of-living conventions of federal and state DB plans. WP2's worked examples come from IRS publications; each statutory figure above is checked against its source in WP2 before use.

**The gate, WP-G** (WP5), scores M0 and M1 on held-out PSID waves. Proposal, to be frozen at IR0: candidates use information through the 2013 wave; the gate scores the 2017–2023 waves for the 2013 roster on its realized support, so survival and family events are the PSID's own and the gate isolates the wealth and pension law, as gate m6's replay did for earnings (Track B §2, "the replay function"). Cells by age band and sex: net-worth quantiles; the share whose countable liquid assets sit below SSI's limits; DC ownership and balance quantiles; DB receipt at 62 and over; pension-income receipt. Floors come from household half-samples, as B2's did (`docs/parity-ledger.md:91, 165`).

**External checks** (WP8) — the SCF 2019 and 2022, the Federal Reserve's Financial Accounts, DOL Form 5500 statistics, IRS SOI IRA tables, SIPP — are report-only and frame-relative until the projection starts from a representative population.

**Output concepts** (WP6). The comparison targets measure income differently from the PSID, so WP6 adds the concepts they use: MINT8's household income sources (Social Security, annuitized asset income from DC plans and savings, DB pension income, earnings, coresident income; MINT8 Table User Guide, committed capture `data/external/mint8_table_user_guide.source.html`) and Butrica and Uccello's annuitized financial assets, which `adjusted_poverty.py` already prices. The annuity code is reused, not copied.

### 3.3 SSI

**Rules come from PE-US; the projection supplies its inputs.** SSI0 pins a PE-US release with resource deeming (2.53.1 or later) and extends the bridge's person inputs to what SSI needs: ABD status, blindness, stock and bond assets, retirement-account balances, living-arrangement inputs and take-up. SSI1 projects SSI's parameters past PE-US's last realized year by the statute: the FBR by 42 U.S.C. 1382f(a) on the projection's COLA path, the resource limits and income exclusions fixed in nominal dollars, and state supplements frozen at the last realized year, a named assumption. The overrides enter through `RunCase.parameter_overrides`.

**Conformance before population** (SSI2, gate SSI-C). Worked examples from POMS and 20 CFR part 416: income exclusions, earned income, spousal and parental deeming including the 416.1163(e)(2) cap, resources including retirement funds under POMS SI 01120.210, couple computation, living arrangements and in-kind support. Differential checks run against rulespec-us where it encodes the section and against exercise 2's static offset as a special case. Configurations PE-US gets wrong are refused and counted, never dropped from denominators, as G does. Each PE-US discrepancy found is filed upstream with its rulespec-us mirror, under PolicyEngine's mirror rule.

**First admission covers the aged** (SSI3). People 65 and over are categorically eligible by age. Blind and disabled adults need a disability determination that does not depend on insured status, which the engine lacks: its DI awards never check insured status and are fitted to data through 2008 (`docs/parity-ledger.md:98`). They are flagged unsupported and stay in denominators. SSI7 adds them after Track B's B4 and an insured-status rule (decision 4, §12).

**Take-up is estimated, not aligned** (SSI4). Take-up is modelled on SIPP person-months and PSID family units: eligibility simulated through PE-US, receipt as reported, as a function of potential benefit, age, sex, marital state, Social Security receipt and living arrangement. Survey misreporting of SSI as Social Security is a named limitation. Aligning to SSA's caseloads instead would be a methodology choice the engine has not made (`docs/parity-ledger.md:112`).

**The gate, SSI-G** (SSI5): aged SSI receipt by age band, sex and marital state in held-out PSID waves and a held-out SIPP panel, and mean payment among recipients relative to the FBR. SSA's aged caseloads by age (SSI Annual Statistical Report; Annual Statistical Supplement section 7) are reported beside it, frame-relative.

**Inside the projection** (SSI6): each projected year runs through PE-US with Social Security from the engine, resources, pensions and asset income from WP, and earnings from Track B once admitted. Projected caseloads, payments and the poverty effect of a Social Security cut are report-only until the population is representative. SSI's estimands here are annual (December receipt or annual payments); monthly flows depend on event timing and would need Track B's I and its observational timing gate.

### 3.4 Other income

Veterans' benefits, unemployment and workers' compensation, child support, alimony and coresident income are carried from the starting population by M0's rank rule and are not gated in this design. A target that needs them gated says so in its scope matrix (Track B §3.4, B7).

### 3.5 Comparisons with DYNASIM and MINT

Comparisons come after the gates and are never validation (Track B §3.2, B7). Each is a registered one-shot under Track B §5.4's B7 requirements: a sealed comparator with two transcriptions, a blind builder under an updated `RESTRICTED-FILES.md`, a hashed forecast before the run, and a one-shot at a registered commit with the seal opened after the artifact commit. §6 names the targets.

## 4. Milestones

### 4.1 Milestone table

Rows marked † are conditional and are excluded from the base totals in §4.3.

| Id | Deliverable | Verification or gate | Effort estimate (d / lw) | Depends on | Unlocks |
|---|---|---|---|---|---|
| **IR0** | Source, exposure, access and power audit for every gate in this lane: CE-G, WP-G, SSI-G, and the target definitions of C1–C3. Reuses B0.2's protocol (PR #554, draft) | A written record per gate freezes Track B §5.2's ten elements and the named power procedure before that gate registers. It records exposure already on file (§7.2). A blinded review checks feasibility and power | 5–8 / 1.25–2 | D1–D4 (sources to audit); B0.2's frozen protocol | Registration of CE-G, WP-G and SSI-G |
| **D1** | PSID income, wealth and pension readers: wealth supplements 1984, 1989, 1994, 1999, 2001 and 2003 (not staged; PSID Data Center, Max's registered account); family-file wealth 2015–2023; pension-section items outside 2005–2013; SSI, pension and asset-income items for every wave used, all label-verified as `family_income.py` is | Exact labels at read time; reconciliation of WEALTH1 with its components; refusal of unstaged or unadjudicated files; tests on invented files | 10–14 / 2.5–3.5 | Wealth-supplement download | WP1, WP3, SSI4, IR0 |
| **D2** | SIPP readers, 2018–2024 annual panels: SSI and OASDI receipt and amounts, assets and debts, retirement accounts, pension coverage and income, disability, living arrangement. Variables verified against the Census SIPP API as `sipp_jobs.py` does | Label checks against the API; structure-only tests; refusal of unverified years | 5–8 / 1.25–2 | None | SSI4, WP8, IR0 |
| **D3** | SCF reader, 2019 and 2022 (2025 if released): retirement accounts, DB coverage, net worth, with implicates and replicate weights | Codebook label checks; implicate handling tested on invented data | 3–4 / 0.75–1 | None | WP8 |
| **D4** | Pinned captures and parsers for aggregate tables: SSA Annual Statistical Supplement sections 4 and 7, SSI Annual Statistical Report, State Assistance Programs for SSI Recipients, published counts of noncovered state and local employees, Census Annual Survey of Public Pensions, Federal Reserve Financial Accounts retirement tables, DOL Private Pension Plan Bulletin, IRS SOI IRA tables, BLS NCS benefits | Each capture hashed, with URL and retrieval time; parsers print structure only before registration; no Trustees Report cost table | 4–7 / 1–1.75 | None | CE3, CE4, SSI5, WP8 |
| **CE0** | CE v2 design note, successor to `covered_earnings_correction.md`, after Max's ruling on the campaign (decision 1) | One review round; nothing registered | 2–4 / 0.5–1 | Decision 1 | CE1, CE2 |
| **CE1** | Coverage-rule registry, 1951 onward, with effective dates, citations and worked examples (§3.1, part 1) | Statutory conformance on worked examples; refusal of a year with no rule | 4–6 / 1–1.5 | CE0 | CE3 |
| **CE2** | PSID job-context crosswalk for 1968–2001, and value-code adjudication of the government, industry, occupation, self-employment and state items in every wave 1968–2023 | Label verification per wave; raw tokens kept; codes adjudicated against codebooks and setup files | 6–9 / 1.5–2.25 | CE0 | CE3 |
| **CE3** | Classifier: rule-decided statuses, probabilistic state and local noncoverage from D4, the four statuses and the wage-first cap order; invented-data tests | The invariants in §9; property tests | 5–7 / 1.25–1.75 | CE1, CE2, D4 | CE4 |
| **CE4** | Gate CE-G on EPUF, 1968–2006, with floors, bite check and power; block draft; two referee rounds; registration package for #42 | Registered gate (§3.1, part 4). Section 4 totals report-only | 6–9 / 1.5–2.25 | CE3, IR0 | CE5 |
| **CE5** | One-shot run, publication, and the person-year handoff table for H, B5 and national payroll | The gate's verdict; the handoff schema's invariants | 2–3 / 0.5–0.75 | CE4 | H's covered channel; B5's RET-countable earnings; Registration 18 and M7 payroll |
| **WP1** | Starting states: PSID-start wealth components and pension states; the Microcosm-start map (shared with Microcosm-start T10's table) and requests to Microcosm for DC balances, DB coverage and home value | Accounting identities; refusal of missing components | 4–6 / 1–1.5 | D1 | WP3, WP4 |
| **WP2** | Retirement-plan rule layer (§3.2): RMDs, the early-distribution tax, contribution limits, DB cost-of-living conventions | Statutory conformance on IRS and plan worked examples | 4–6 / 1–1.5 | None | WP4, SSI2 (retirement-fund value) |
| **WP3** | M0, the rank-preserving null, on the PSID panel, and the report-only check A1 (shared with Microcosm-start T10) | Reproduces the plan's rule on invented panels; A1 report-only | 3–5 / 0.75–1.25 | WP1 | WP5 (as null) |
| **WP4** | M1, donor trajectories for wealth components and pension states, with event rules; built on invented data | The invariants in §9; property tests | 10–15 / 2.5–3.75 | WP1, WP2 | WP5 |
| **WP5** | Gate WP-G on held-out PSID waves (§3.2), with floors, bite check (M0 must fail the cells its known flaw predicts) and power; block draft; two referee rounds; registration package | Registered gate | 7–10 / 1.75–2.5 | WP3, WP4, IR0 | WP6 |
| **WP6** | One-shot run and publication; the output layer of MINT8 and Butrica–Uccello income concepts | The gate's verdict; concept reconciliation tests | 3–5 / 0.75–1.25 | WP5 | SSI6, C1–C3 |
| **WP7** † | M2, structural DC and DB accumulation (§3.2) | Re-scored by WP-G as a new candidate; a new attempt on the ledger | 12–18 / 3–4.5 | WP-G failure or a reform-response need; decision 2 | WP-G retry |
| **WP8** | External checks on a representative population: SCF, Financial Accounts, Form 5500, SOI, SIPP | Report-only, frame-relative | 3–5 / 0.75–1.25 | WP6, D2, D3, D4; a representative start | Report |
| **SSI0** | Rules-engine interface: PE-US pin with resource deeming, extended person inputs, parameter overrides; upstream filing of the retirement-fund gap with its rulespec-us mirror | Bridge tests on invented households; the pin's source check | 3–5 / 0.75–1.25 | None | SSI1, SSI2 |
| **SSI1** | SSI parameter projection by 42 U.S.C. 1382f(a), with nominal limits and frozen state supplements | Statutory conformance against SSA's published FBR history; differential against rulespec-us's 1382f encoding | 2–3 / 0.5–0.75 | SSI0 | SSI2, SSI6 |
| **SSI2** | Gate SSI-C: POMS and CFR worked examples, differentials, refused-configuration accounting | Statutory conformance gate, registered | 6–9 / 1.5–2.25 | SSI0, SSI1, WP2 | SSI4 |
| **SSI3** | Categorical status v1: aged only; blind and disabled adults flagged unsupported | Denominator conservation | 1–2 / 0.25–0.5 | SSI2 | SSI4 |
| **SSI4** | Take-up model on SIPP and PSID (§3.3) | Fitted on the training partition IR0 freezes | 8–12 / 2–3 | SSI3, D1, D2 | SSI5 |
| **SSI5** | Gate SSI-G on held-out PSID waves and a held-out SIPP panel, with floors, bite and power; block draft; two referee rounds; registration package | Registered gate. SSA caseloads report-only | 6–9 / 1.5–2.25 | SSI4, IR0, D4 | SSI6 |
| **SSI6** | SSI inside the projection, each year through PE-US; report-only projected caseloads, payments and the poverty effect of a Social Security cut | Identical-policy equality; Registration 19's identity (§9); report-only | 5–8 / 1.25–2 | SSI5, WP6; the engine; Track B earnings when admitted | C1–C3; the poverty row |
| **SSI7** † | Blind and disabled adults: a disability determination without insured status, shared with DI's process; concurrent receipt | Registered gate against held-out SSA blind and disabled caseloads | 10–15 / 2.5–3.75 | B4; an insured-status rule; SSI5 | SSI by type |
| **C0** | Comparator protocol for C1–C3: validation-lane briefs, transcription specifications, values-scan scripts, `RESTRICTED-FILES.md` entries before any builder starts, registration drafts | Review of the briefs; entries made by the orchestrator | 3–5 / 0.75–1.25 | IR0 | C1–C3 |
| **C1** | DYNASIM3 income and wealth at 67 (Butrica and Uccello 2004): arm (a) PSID-realized outcomes in the comparator's income concept, as U2 does for poverty; arm (b) the model projected from the B3L boundary | Registered one-shot comparison. Comparator lane 4–6 d, run and comparison 4–6 d | 8–12 / 2–3 | Arm (a): C0 and WP6's concept layer. Arm (b): also WP-G, SSI-G, B3L and B4 | The wealth row's DYNASIM comparison |
| **C2** | MINT8 current-law profiles, 2024 and 2030 | Registered one-shot comparison. Comparator 3–5 d, run 3–5 d | 6–10 / 1.5–2.5 | C0, WP6, SSI6; a representative start (d947); an admitted projection to 2030 (J, B7) | MINT rows of the income and group rows |
| **C3** | DYNASIM4 baseline income of people 62 and older (Urban's published output) | Registered one-shot comparison. Comparator 3–5 d, run 3–5 d | 6–10 / 1.5–2.5 | As C2 | DYNASIM4 rows |

### 4.2 Verification class, admitted scope and the ledger rows each milestone closes

Track B's classes are used unchanged (Track B §3.2), with its "accounting conformance" label for identity checks.

| Id | Verification class | Admitted scope on success | Ledger row and the part it closes |
|---|---|---|---|
| IR0 | Source audit | Nothing scientific; authorizes registration of the named gates on the frozen records | None directly |
| D1–D4 | Accounting conformance | Readers for the listed waves, tables and variables only | None directly |
| CE1 | Statutory conformance | Coverage rules for the listed years and categories | Covered earnings: the rule basis |
| CE4/CE5 | Held-out prediction on EPUF where IR0 certifies EPUF unused for coverage; otherwise retrospective regression | The split for 1968–2006 PSID careers on the registered cells; frame-relative | **Covered earnings: "a covered/noncovered split of PSID earnings" and "a fresh gate on the public-use file"**; the SSA-totals check stays report-only until a representative population exists |
| WP2 | Statutory conformance | Plan rules for listed years | None directly |
| WP3 | Report-only (A1) | Nothing admitted | None |
| WP5/WP6 | Held-out prediction on waves IR0 certifies unused; otherwise retrospective regression | Wealth and pension states for the registered roster, ages, waves and cells, on realized support | **Wealth: "first against later PSID waves the model did not see"** |
| WP8 | Report-only | Nothing admitted | Wealth: context on a representative population |
| SSI2 | Statutory conformance (registered gate) | SSI computations for supported configurations | **SSI: "eligibility, resource, deeming and state-supplement worked examples"** |
| SSI5 | Held-out prediction | Aged SSI receipt and payments on the registered cells | **SSI: "participation against SSA caseloads by age"** for the aged; by type waits for SSI7 |
| SSI6 | Accounting conformance plus report-only projections | Mechanics only | SSI: "projected caseloads, payments and the poverty effect of a Social Security cut", report-only until representative |
| SSI7 † | Held-out prediction | Blind and disabled adult SSI | SSI: participation by type |
| C1 | Registered held-out comparison with DYNASIM3 | Agreement or disagreement on the frozen cells only; not validation | **Wealth: "then against DYNASIM's published tables"**; poverty and results-by-group rows, for those cells |
| C2, C3 | Registered comparison with MINT8 and DYNASIM4 | As C1 | Poverty and income distribution; results by group (MINT rows) |

The ledger rows are closed in full only when every part has its evidence. Covered earnings closes at CE5 except its SSA-totals part. Wealth closes after WP6 and C1. SSI closes after SSI5, SSI6 on a representative population, and SSI7.

### 4.3 Totals, lanes and critical path (all estimates)

| Group | Rows | Estimate |
|---|---|---|
| Shared audit | IR0 | 5–8 d |
| Data | D1–D4 | 22–33 d |
| Covered earnings | CE0–CE5 | 25–38 d |
| Wealth and pensions | WP1–WP6, WP8 | 34–52 d |
| SSI | SSI0–SSI6 | 31–48 d |
| Comparisons | C0–C3 | 23–37 d |
| **Base total** | | **140–216 engineer-days, or 35–54 lane-weeks** |
| Conditional, not in the base | WP7, SSI7 | 22–33 d |

**Shared with the Microcosm-start plan.** If d947 proceeds and that plan builds T3, T10 and T12 first, D1 shrinks by about 3–4 d (T3's wealth readers), WP1 and WP3 by about 5–8 d (T10's table, rule and A1), and SSI6 by about 3–5 d (T12's yearly PE-US machinery). Built once for both plans, the base falls to about 129–199 d. This design counts them here because d947 is parked.

**Expected rework.** The coordinator records that 5 of 8 gated first attempts in this repository have failed (`parity-forecast-20261021.md:45`). This lane has three empirical gates (CE-G, WP-G, SSI-G). Pricing each retry as its candidate milestone plus one week of design and review (CE3 + 4 = 9–11 d; WP4 + 4 = 14–19 d; SSI4 + 4 = 12–16 d), the expected rework at the observed rate is 5/8 × 35–46 d ≈ **22–29 d**. Central estimate with rework: **about 162–245 engineer-days**. SSI-C is a conformance gate; the rules lane's conformance milestones have needed fix rounds rather than retries (G v2's fifteen; `parity-forecast-20261021.md:44`), and SSI2's range is set with that in mind.

**Lanes.** Four lanes run at once after approval: a data-and-audit lane (D1, D4, D2, D3, then IR0), and one lane each for CE, WP and SSI. Each lane runs its rows serially. Elapsed times below are engineer-day equivalents from the start, at 4 engineer-days a lane-week.

- Data-and-audit lane: D1 ends at 10–14, D4 at 14–21, D2 at 19–29, D3 at 22–33 and IR0 at **27–41 d**.
- WP lane: WP2 (4–6) runs while D1 does. WP1, WP3 and WP4 follow D1 and end at 27–40; WP5 waits for IR0 and ends at 34–51; WP6 ends at **37–56 d**.
- CE lane: CE0, CE1 and CE2 end at 12–19; CE3 waits for D4 and ends at 19–28; CE4 waits for IR0 and ends at 33–50; CE5 ends at **35–53 d**.
- SSI lane: SSI0–SSI3 end at 12–19 (SSI2 uses WP2, done by then); SSI4 waits for D2 and ends at 27–41; SSI5 waits for IR0 and ends at **33–50 d**; SSI6 waits for WP6 and ends at **42–64 d**.

So all three gates' first attempts are published after about **37–56 engineer-day equivalents, or 9.25–14 weeks**, and SSI inside the projection after 42–64, or 10.5–16 weeks, excluding queues and holidays. Started in early November 2026, that is January to late February 2027. IR0 sits on the path: at the high end it delays every gate. None of it waits on B2's successor.

The comparisons wait on prerequisites. C1's arm (a) needs only C0 and WP6's concept layer. Its arm (b) needs B3L and B4, whose windows the coordinator puts at 9 December 2026 to 11 February 2027 if every gate passes first time (`parity-forecast-20261021.md:62–63`). C2 and C3 need a representative start and an admitted projection to 2030, after J and B7: around August 2027 in the coordinator's central case (`:79`).

### 4.4 Against the coordinator's estimate

| Row | Coordinator (order of magnitude) | This design (first attempt) | Why they differ |
|---|---|---|---|
| Covered earnings | 8–12 d | 25–38 d, plus shares of D4 and IR0 | The PSID job context before 2003 is unread, the government item's codes are unadjudicated, and a gate on EPUF needs floors, bite, power and two referee rounds |
| SSI in the projection | 10–20 d | 31–48 d, plus shares of D1, D2, D4 and IR0 | Take-up must be estimated, PE-US needs new inputs and a conformance gate, and the gate needs a SIPP reader the repository lacks |
| Wealth, pensions and other income | 30–60 d | 34–52 d, plus D1 and D3 | The model work lands inside the coordinator's range; the readers and the audit are extra |
| Not in the coordinator's rows | — | Data readers 22–33 d; IR0 5–8 d; comparisons 23–37 d | The coordinator's rows cover building, not the data, audit and comparator-lane work the gates and comparisons need |

The coordinator's three rows total 48–92 d. This design's base total is 140–216 d, about 2.3–2.9 times as much, and its central estimate with rework 162–245 d. The difference is mostly work the coordinator's rows did not list.

## 5. Data sources and access per gate

Status as of 21 October 2026. "Staged" means the files are on this machine and a reader exists or is named. Access details for unstaged sources are confirmed in D1–D4 and frozen at IR0. SIPP, SCF and HRS microdata are not staged (`~/PolicyEngine/sipp-data` does not exist).

| Gate or use | Source | Role | Access | Lead time | Staged |
|---|---|---|---|---|---|
| CE-G | SSA 2006 EPUF, 1 percent sample, 1951–2006 | Gate truth | Public download | None | Yes (`epuf.py`) |
| CE-G | PSID family files 1968–2023 | Model input | PSID registration (Max's account) | None | Yes |
| CE3, CE-G context | SSA Annual Statistical Supplement section 4 (covered workers, taxable earnings); published counts of noncovered state and local workers; Census Annual Survey of Public Pensions | Classifier inputs; report-only context | Public | None | No (D4) |
| WP-G | PSID wealth: supplements 2005 and 2007; family-file composites 2009–2023 | Training and held-out waves (split at IR0) | PSID registration | None | Yes |
| WP-G | PSID wealth supplements 1984, 1989, 1994, 1999, 2001, 2003 | Training history | PSID Data Center, login-gated | About a day | No (D1) |
| WP-G | PSID pension section (plan type, balances, expected benefits, receipt) | Training and held-out | In the family files | None | Read for 2005–2013 only |
| WP8 | SCF 2019, 2022 (2025 if released) | Report-only context | Public download | None | No (D3) |
| WP8 | Federal Reserve Financial Accounts; DOL Private Pension Plan Bulletin; IRS SOI IRA tables; BLS NCS | Report-only context | Public | None | No (D4) |
| SSI-C | 20 CFR part 416; POMS SI chapters; 42 U.S.C. 1381–1383f | Worked examples | Public | None | Partly (§2.5 captures) |
| SSI-C | PE-US release (PyPI); rulespec-us (GitHub) | Rules engine; differential | Public | None | 2.18.0 installed; 2.53.1 wheel downloaded |
| SSI4, SSI-G | SIPP 2018–2024 panels | Take-up training; one panel held out | Public download | None | No (D2) |
| SSI4, SSI-G | PSID head and wife SSI items | Take-up training; held-out waves | In the family files | None | Read for 2005–2013 only |
| SSI-G context | SSA SSI Annual Statistical Report; Annual Statistical Supplement section 7; State Assistance Programs for SSI Recipients | Report-only context | Public | None | No (D4) |
| Excluded | HRS and RAND HRS; SSA-linked restricted files (HRS, SIPP Gold Standard File) | Not used; would strengthen pension wealth and take-up | Registration; restricted access | Months for restricted files | No; unpriced (§11) |

Exposure on file for these sources is listed in §7.2.

## 6. Comparison targets

These are the DYNASIM and MINT tables this lane would be compared with. **The design's author has opened none of their results.** Each target's titles come from a page the restricted list lets builders read, or from the repository's committed MINT8 guide; every cell is for a validation-only lane to transcribe and seal (C0).

- **DYNASIM3: Butrica and Uccello (2004), *How Will Boomers Fare at Retirement?*** Its list of tables (PDF pages 6–7, which the restricted list lets builders read) names, for individuals at age 67: household wealth (mean, median, by source; Tables 2–5), household income (mean, median, by source; Tables 8–11), replacement rates (Tables 13–14), the share below 200 percent of the poverty level and below 45 percent of the national average wage (Tables 22–23), and appendix tables of wealth and income by source, gender and marital status (appendix Tables 3–16 and 18). Exercise 2 used Tables 19 and 21, and U2 uses their 1946–55 column. Every results table of the report is restricted for builders (`RESTRICTED-FILES.md`, exercise 2). C1 needs the cohort columns whose 67th birthdays the PSID records; IR0 and C0 fix which.
- **MINT8 current-law profiles.** SSA publishes, for 2024, 2030, 2050 and 2070, profiles of beneficiaries aged 60 or older and of taxpayers aged 31 or older, with the household income distribution and mean shares by source (Social Security; annuitized asset income from DC plans and savings; DB pension income; all earnings, covered and noncovered; coresident income), household wealth including retirement accounts and excluding home equity, covered earnings, and poverty under the official and supplemental measures, overall and by race and ethnicity (MINT8 Table User Guide, committed capture `data/external/mint8_table_user_guide.source.html`, the sections "Interpreting the Profile of Beneficiaries" and "of Taxpayers"). Their 2024 cells can also be set beside observed 2024 survey data. The profile pages are not on the restricted list today; C0 adds them before any builder starts, as the A-COLA registration did for its sources.
- **DYNASIM4: Urban's published output.** The ledger cites Urban's DYNASIM output repositories, among them `dynasim-shiny2`, "Mean Income of People 62 and Older under Social Security Reform Options" (`docs/references.bib`, `urban2018dynasimshiny2`). They are restricted for builders whole (`RESTRICTED-FILES.md`, NASI follow-ups). C3 would use their current-law rows only, through a validation-only lane.
- **Not comparison targets but validation sources:** EPUF; SSA's covered-worker, SSI and caseload tables; the SCF, SIPP and the Financial Accounts. They test the model; DYNASIM and MINT only sit beside it.

Any DYNASIM or MINT page that reports a reform's effect stays restricted under the existing entries, and C1–C3 use none of them.

## 7. Admission criteria and registration discipline

### 7.1 Rules

Track B §5.1 applies unchanged: each stage a new module and a new registered version; no edits to `engine/loop.py`, `engine/steps.py`, `gates.yaml`, committed `runs/*.json` or `src/populace_dynamics/track_b/`; everything frozen before any real-data outcome; exclusive output paths; published abort records. Track B §5.2's uncertainty rule applies to every empirical gate here: simultaneous 95 percent bounds over a registered cell family, survey-design resampling with family clusters, Monte Carlo error below a tenth of the tolerance, and insufficient precision reported as inconclusive, never as a pass.

Every gate and comparison is registered on issue #42 before it runs. Registrations are Max's; this lane drafts them and the coordinator brings them to him. Development and tests use invented data only. No real-PSID statistic is computed outside a registered step, and no small-cell PSID count goes to GitHub.

### 7.2 Exposure already on file

IR0 records these before proposing any holdout:

- **Exercise 2 (Registration 16)** used PSID income, SSI and WEALTH1 for the 2005–2013 waves, at age 67, with results public on #42.
- **U2's step 4** computes, before registration, WEALTH1 quantiles, SSI receipt and recipient means by income year for the family units of the 1946–55 cohort around age 67, in waves through 2023 (`docs/design/boomers2004_1946_55_comparison.md:565–575`). Those waves overlap WP-G's and SSI-G's proposed holdouts. This design's author has not opened U2's step-4 outputs, and the builders of this lane's gates do not open them.
- **Registration 19** published static SSI and asset-test results on Microcosm's 2024 frame.
- **Gate 1, gate m6 and B2** used PSID earnings through 2022; they used no wealth, pension or SSI item.
- **`gate_epuf_fill`** used EPUF to certify career fills; it scored no coverage classification.

"Later" or "external" does not by itself make a holdout unused (Track B §5.2).

### 7.3 Stage rules

- **CE-G.** The bite check is mandatory: the all-covered proxy must fail the cells CE v2 claims to improve, or the gate is vacuous and stops before any candidate result (`WEAK_POWER_OR_VACUITY`). EPUF's disclosure operator (random rounding, band means near the cap; `epuf.py:20–28`) enters the floors.
- **WP-G.** M0 and M1 are both scored; M1 is admitted only if it passes, whatever M0 does. A pass on exposed waves is retrospective regression evidence only.
- **SSI-C.** A refused configuration stays in every denominator. Agreement with PE-US or rulespec-us is diagnostic, not statutory acceptance (Track B §6, "Axiom coverage matrix").
- **SSI-G.** Take-up is fitted only on the training partition. SSA caseloads never tune it.
- **C1–C3.** Track B §5.4's B7 requirements, and Track B §3.4's no-behavioral-response primary specification where the comparator assumes none.

## 8. Interfaces

### 8.1 Track B

This lane edits nothing under `src/populace_dynamics/track_b/`. It hands outputs to Track B through declared schemas and consumes Track B's outputs the same way.

- **H, the history recorder v2.** Track B's H keeps "labor, covered and RET-countable earnings kept separate" for 2010–2030 (Track B §3.1). CE5 supplies the source values of those channels for every PSID person-year from 1968, with status probabilities and the unresolved share, in a versioned table H reads. H owns recording; CE owns classification. Until CE5 passes, H's covered channel carries the legacy label "labor-income proxy".
- **B5, the earnings test in the projection.** The test counts noncovered wages and excludes pension payments (42 U.S.C. 403(f)(5)(C); §2.5). B5 therefore needs CE's RET-countable channel, not covered earnings, and WP's pension income never enters it. Without CE5, B5 must treat projected labor earnings as all covered and say so.
- **J, joint validation.** J tests "joint earnings–claiming–DI states, payment and recipient denominators, and survivor pathways" on estimands frozen at B0.2 (Track B §3.4). This lane adds no estimand to J on its own. If SSI-G passes before B0.2 freezes J's record, it proposes concurrent Social Security and SSI receipt as a J estimand, for B0.2's blinded ratification; otherwise J excludes SSI.
- **B7.** Track B's scope matrix requires each target's "required non-Social-Security income" (§3.4). A B7 target that needs pensions, asset income or SSI is blocked until WP-G and SSI-G pass, and SSI7 for SSI under 65.
- **B4.** SSI7 needs B4's DI outcomes. WP's widowhood rule uses B4's endogenous widowhood once admitted; before that, WP-G runs on realized support.
- **B0.2.** IR0 reuses B0.2's protocol and record format (PR #554). Whether IR0's records sit inside B0.2's or beside it is the coordinator's call.
- **I.** SSI is a monthly program. This lane's SSI estimands are annual; any monthly SSI estimand would need I's observational timing gate (Track B §3.4).

### 8.2 PolicyEngine-US and Axiom

- **PE-US computes SSI's rules**; this lane supplies inputs and projected parameters and never re-implements SSI's federal rules in Python. The existing static offset in `adjusted_poverty.py` stays as exercise 2's registered rule and becomes one differential case in SSI2.
- **The pin moves forward deliberately.** The bridge defaults to 2.18.0. SSI0 pins a release with resource deeming (2.53.1 or later), records the change in a new run configuration, and leaves Registration 19's ratified 2.18.0 run untouched.
- **Known gaps, refused or filed:** retirement funds as resources (§2.4); the spousal-deeming cap (Registration 19 §12, item 12); state supplements outside the encoded states. Each is filed on policyengine-us with a rulespec-us issue labelled `pe-parity`, under PolicyEngine's mirror rule.
- **The interface layer.** PolicyEngine's guidelines prefer policyengine.py over PE-US internals. SSI0 decides whether the SSI projection runs through the existing subprocess bridge, which reads the model's own variable tree, or through policyengine.py, and records why.
- **Axiom.** Where rulespec-us encodes an SSI section (§2.4), SSI1 and SSI2 run differential checks against it. The coverage matrix is published with SSI2; agreement is diagnostic only.

### 8.3 Microcosm and the Microcosm-start plan

- The frame lacks DC balances, DB coverage and home value (`microcosm-start.md:282`), and microcosm#1215, open, concerns resources on the frame. WP1 files the requests with evidence. A Microcosm start cannot carry WP's pension states until they are met.
- WP3 is the Microcosm-start plan's rule and its check A1; T3, T10 and T12 overlap D1, WP1, WP3 and SSI6 (§4.3). Whichever plan builds a shared piece first owns it.

## 9. Invariants and tests per component

Each invariant below is stated in the PR that builds its component and tested with property-based tests (Hypothesis) beside example tests. Where two implementations of the same rule exist, a differential test checks they agree.

- **Coverage classifier (CE3).**
  - The four status probabilities are nonnegative and sum to one exactly.
  - Conservation: covered wages, covered self-employment, noncovered and unresolved earnings sum to the person-year's adjudicated labor income.
  - Statutory order: taxable wages are min(wages, cap); taxable self-employment is min(SE, max(0, cap − taxable wages)); no self-employment loss offsets wages; capped amounts never exceed the year's taxable maximum.
  - Zero preservation: zero labor income gives zero in every channel.
  - Monotonicity: raising a component's noncoverage probability never raises its expected covered taxable amount.
  - RET-countable earnings equal covered wages plus noncovered wages plus net self-employment earnings, and never include pension payments.
  - Determinism under keyed draws; invariance to row order.
- **Wealth and pensions (WP1–WP6).**
  - Accounting identity: net worth equals assets less debts for every unit and wave; person allocations sum to the household's.
  - Balances are nonnegative; withdrawals never exceed balances; required minimum distributions are met when they apply.
  - Events conserve: widowhood moves the household's assets to the survivor without creating any; a divorce split sums to the pre-divorce total; a death's assets leave as a recorded exit.
  - DB receipt, once started, is absorbing until death.
  - M0: equal input ranks give equal outputs; M1: a donor's trajectory is applied only from information at or before the boundary (perturbing post-boundary data leaves fitted states unchanged, Track B §6's B2 test).
  - The annuity in WP6 reuses `annuity_factor_single` and `annuity_factor_joint`; a differential test checks WP6's income concept against exercise 2's on the same invented rows.
- **SSI (SSI1–SSI6).**
  - SSI is nonnegative and at most the applicable FBR plus any state supplement.
  - Above the general exclusion and while SSI is positive, each dollar of unearned income lowers SSI by one dollar; beyond the earned-income exclusions, each dollar of earnings lowers it by fifty cents.
  - SSI never rises when countable income or countable resources rise, all else fixed.
  - The projected FBR is nondecreasing for a nonnegative COLA and is a multiple of $12 a year.
  - Registration 19's identity: SSI with the asset test equals SSI without it times the resource-test indicator (`pe_us_depletion_cut_population.md` §4.2).
  - Exercise 2's offset is the special case "existing recipients, no new eligibility": a differential test checks SSI2's computation against `_ssi_response` on invented rows.
  - Identical-policy baseline and reform runs match exactly.
- **Comparisons (C1–C3).** Definitions, denominators and cells are frozen before unsealing; no cell is selected or dropped afterwards; unsupported cells stay reported.

## 10. Risks and kill criteria

### 10.1 Blocking rule

Track B's rule applies unchanged (Track B §7): required-source unavailability, unresolved exposure, inadequate precision, unsupported critical configurations, or a failed gate or required regression test block the corresponding admission and its dependants. Fallbacks register before candidate outcomes. Failed or unsupported cells stay reported, and removing them cannot manufacture a pass.

### 10.2 Named conditions and what each stops

| Condition | Trigger | Stops |
|---|---|---|
| `COVERAGE_UNIDENTIFIED` | CE2 finds waves with no government-level or state information, so the unresolved share of a gated cell exceeds the limit IR0 freezes | CE-G for those cells; they stay report-only and `unresolved` |
| `EPUF_CONCEPT_MISMATCH` | EPUF's disclosure operator or its zero-row convention makes a cell's floor uninformative | That cell; if the gate's core cells, CE-G (prospective rescope) |
| `WEALTH_WAVE_GAP` | Pre-1999 waves are five years apart, so donor transitions before 1999 cannot be two-year | M1 uses biennial transitions from 1999; earlier waves inform starting states only |
| `EXPOSURE_UNRESOLVED` | IR0 cannot establish an unused holdout (for example because of U2's step 4) | The predictive label; a pass is regression evidence only |
| `WEAK_POWER_OR_VACUITY` | Power below 0.90, undefined cells or a vacuous bite check | That gate, pending a prospective rescope registered before candidate results |
| `SOURCE_UNAVAILABLE` | A wealth supplement or SIPP panel cannot be obtained or verified | The gates that need it |
| `RULES_ENGINE_GAP` | PE-US or rulespec-us cannot compute a configuration correctly | Those configurations, refused and counted; targets needing them blocked |
| `TAKEUP_UNIDENTIFIED` | SSI-G fails or is inconclusive on take-up | Projected SSI caseloads; only full-take-up potential SSI is published, labelled as Registration 19's headline basis was |
| `DISABILITY_LINK_UNADMITTED` | No admitted disability determination without insured status | SSI under 65 (SSI7) |
| `FRAME_LACKS_RESOURCES` | Microcosm's frame lacks DC balances, DB coverage or home value | WP and SSI on a Microcosm start; PSID-start results continue |
| `RETURN_PATH_UNRULED` | No ruled return assumption for DC balances | M2 (WP7) |
| `REPRESENTATIVE_START_MISSING` | No representative starting population (d947 parked; frame not certified) | WP8, SSI6's national figures, C2 and C3 |
| `COMPARATOR_EXPOSED` | A builder of this lane opened a C1–C3 result | That comparison's blind label |
| `GATE_FAIL_OR_REGRESSION_FAIL` | A registered gate here fails | Its admission and dependants; published with no seed selection or tolerance relief |
| `SUCCESSOR_EXHAUSTED` | Two independently justified successors of one mechanism fail | That mechanism, pending new evidence |

### 10.3 Kill criteria

1. **Covered earnings.** If CE4's bite check finds that EPUF cannot tell the all-covered proxy from CE v2 on the gate's core cells, the gate stops before any candidate result and CE v2 is published report-only. The ledger row then reads *Built, ungated*, and H's covered channel keeps its proxy label.
2. **Wealth and pensions.** If IR0 finds WP-G's core cells below 0.90 power using every held-out wave, WP-G is rescoped before candidates or becomes report-only, the path `gate_epuf` took. If M1 and one successor (M2 or an M1 revision) both fail, WP projection pauses, the row stays *None* for projection, and every B7 target that needs non-Social-Security income is blocked.
3. **SSI.** If take-up fails twice, the lane publishes only potential SSI at full take-up and stops projecting caseloads.
4. **Track B.** If forward earnings reach `SUCCESSOR_EXHAUSTED`, this lane's gates still stand, since none depends on B2, but C1's arm (b), C2, C3 and SSI6's earnings inputs stop.

### 10.4 Attempt ledger

Each mechanism (coverage classification, wealth and pension transitions, SSI take-up) keeps a cumulative attempt ledger by gate family, as Track B does (Track B §7). Renaming a module or a registration does not reset it.

### 10.5 Risks most likely to slip

- **D1 and CE2.** Label verification across thirty to forty PSID waves is slow, and the covered-earnings campaign's sweep found 46 of 818 official prompts that broke a single-field rule (#403). Both are priced at their upper ends for that reason.
- **SSI4.** Simulating eligibility through PE-US on SIPP person-months is untested here, and survey reports of SSI are known to be confused with Social Security.
- **WP5.** PSID wealth at older ages is thin, so power may force pooling.
- **SSI2.** The rules lane's history (G v2's fifteen fix rounds) says conformance work hardens slowly.
- **Comparisons.** Each depends on prerequisites outside this lane.

## 11. Staffing and scope assumptions behind every estimate

- **Unit of effort.** One engineer-day is one day of reviewed output; one agent lane delivers about 4 engineer-days a week. Both are Track B's assumptions (Track B §8).
- **Four lanes** run at once after approval: data and audit; covered earnings; wealth and pensions; SSI. Each runs its rows serially. Comparisons run later on whichever lane is free.
- **All ranges are engineering judgments**, not demonstrated throughput, and mine unless they cite another document.
- **Excluded from the estimates:**
  - review and registration queues, including Max, the coordinator and referees;
  - HRS and SSA-linked restricted data, their access time and loaders;
  - Microcosm rebuilds and the frame fixes WP1 requests;
  - PE-US and rulespec-us fixes beyond filing them;
  - research after a failed gate, beyond the expected-rework line in §4.3;
  - the conditional rows WP7 and SSI7;
  - Subfleet lane availability.
- **Data.** PSID family files and EPUF are staged and assumed runnable. SIPP and SCF downloads are assumed to need no access time.

## 12. Decisions for Max

Each is a call this design cannot make. The coordinator brings them to Max; nothing below is decided.

1. **Retire the covered-earnings correction campaign and build CE v2?** Recommended. It keeps the old design's estimands and its fitting-free path, and drops the amendment ceremony. The alternative, restarting at Amendment 20, is not priced here.
2. **The return assumption for DC balances.** Needed only for M2 (WP7). The options are a deterministic path built on the selected baseline's interest rate, or a stochastic path. It is a methodology choice.
3. **Which population the income comparisons start from.** PSID cohorts now, or Microcosm's frame once d947 posts and the frame is certified. C2 and C3 need a representative start.
4. **SSI for blind and disabled adults in the first admission, or after B4 (SSI7)?** Recommended: after B4.
5. **Register the comparison families on #42:** DYNASIM3's Boomers 2004 income and wealth tables (C1), MINT8's current-law profiles (C2) and DYNASIM4's published baseline income (C3). Each registration is Max's.
6. **Move the PE-US pin to a release with resource deeming, and run SSI through policyengine.py or the existing bridge.**
7. **Start an HRS restricted-data application now?** It would take months, and it is excluded from this design's estimates. It would strengthen pension wealth and take-up.

## 13. Files and sources read, and exposure

**Read in this run** (master `1e739d32` unless noted): `docs/parity-ledger.md` in full; `docs/design/covered_earnings_correction.md` lines 1–346, 7099–7200, 8145–8200 and 9193–9240, plus its section headings; `src/populace_dynamics/estimates/adjusted_poverty.py` lines 1–430, 840–920 and 1050–1633; `src/populace_dynamics/bridge/policyengine_us.py` lines 1–300; `docs/design/pe_us_depletion_cut_population.md` lines 1–120 and §§2.3–2.4, 4 and 12; `docs/plans/microcosm-start.md` lines 1–60, 253–330 and §4.2; `src/populace_dynamics/data/family_income.py` lines 1–120; `src/populace_dynamics/data/employer_dc.py` lines 1–110; `src/populace_dynamics/data/sipp_jobs.py` lines 1–70; `src/populace_dynamics/data/epuf.py` lines 1–60; `src/populace_dynamics/data/psid_job_context.py` lines 1–60 and `psid_job_context_registry.py` lines 270–320; the docstrings of `covered_wage_history.py`, `historical_coverage_rule_validation.py` and `psid_covered_earnings_registry.py`; `src/populace_dynamics/track_b/README.md`; `src/populace_dynamics/estimates/group_breakdown.py` lines 1–80; `docs/design/boomers2004_1946_55_comparison.md` lines 565–600; `data/external/mint8_table_user_guide.source.html`, structure and the profile sections; issue #403; PR #405's summary; PR #386's summary; the Track B design, revision 3, §§1–8; the coordinator's forecast of 21 October; PE-US 2.18.0's installed SSI variables and 2.53.1's wheel listing and countable-resource parameter; rulespec-us's file list at `5796861e5`; the legal captures in §2.5 and POMS SI 01120.210.

**Exposure statement.** This design's author read `RESTRICTED-FILES.md` first and opened no file, page or line it lists, with one disclosure. To find the readable list of tables in Butrica and Uccello (2004), a script extracted PDF pages 1–9 and printed only per-page counts of three patterns; it then printed pages 6–7 (the list of tables and appendix tables, which builders may read) after a check, with digits masked, that those pages hold nothing else. No text of pages 1–5 or 8–9 was printed. The author opened no comparator, seal, DYNASIM or MINT result, no MINT profile or option page, no U2 step-4 output and no Track B outcome-aware file other than the parity ledger on master, which states B2's public result; the author is not a B2-successor builder. No PSID statistic was computed; PSID directories were listed by name only.
