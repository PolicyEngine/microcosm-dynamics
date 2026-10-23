# Income and resources: covered earnings, wealth and pensions, and SSI

- **Status:** draft revision 3, 23 October 2026, for review. It authorizes no build, registration, real-data run or change to any other design. Nothing in it has run. **Every milestone that reads PSID data is blocked on decision d1899 (§2.7).**
- **Revision 1** applied all eighteen findings of the round-1 review (Subfleet `20261021-102216-ir-design-review-r1`, REVISE; `EV/income-resources-20261021/review-r1.md`), the author's seven findings on revision 0 (`EV/income-resources-20261021/self-review-r0.md`), and the coordinator's correction that the rework rate it cited is a stress assumption, not an observed rate. **Revision 2** applied the round-2 review's twelve new findings and its two partial resolutions (Subfleet `20261022-000434-ir-design-review-r2`, REVISE; `EV/income-resources-20261021/review-r2.md`). **Revision 3** applies the round-3 review's six findings (Subfleet `20261022-004101-ir-design-review-r3`, REVISE; `review-r3.md`), the lane's data-source catalog (Subfleet `20261021-095936-ir-data-sources`; `research/data-sources.md`), and the PSID conditions-of-use finding it surfaced (§2.7). §14 maps every finding to where it is resolved.
- **Authority:** Max authorized this lane on 2026-10-21 (decision d1802). Its first deliverable is this priced design; building waits for his approval of it.
- **Scope:** three rows of `docs/parity-ledger.md` at master `1e739d32`: *Covered earnings and agreement with SSA records*; *Wealth, pensions and other income*; *Supplemental Security Income (SSI)*.
- **Format:** modelled on revision 3 of the Track B design (`~/microcosm-launch-evidence/dynasim-parity-20260909/trackb-design-20260928.md`, approved under d515): its milestone table (§3.1), verification classes (§3.2), admission rules (§5), risks and kill criteria (§7) and staffing assumptions (§8).

**Every effort figure in this document is an estimate.** The figures are engineering judgments under the staffing assumptions in §11, not demonstrated throughput. "d" means engineer-days and "lw" means agent-lane weeks at 4 engineer-days a week; in every cell lw = d ÷ 4 exactly.

Abbreviations: SS is Social Security; SSI is Supplemental Security Income; PE-US is PolicyEngine-US; FBR is SSI's federal benefit rate; ABD is aged, blind or disabled; DB and DC are defined-benefit and defined-contribution pensions; IRA is an individual retirement account; RMD is a required minimum distribution; RET is the retirement earnings test; EPUF is SSA's 2006 Earnings Public-Use File; SCF and SIPP are the Survey of Consumer Finances and the Survey of Income and Program Participation; MINT is SSA's Modeling Income in the Near Term model. `EV` is `~/microcosm-launch-evidence/dynasim-parity-20260909`.

## 1. Purpose

DYNASIM projects, for each simulated person, the income a reform changes: Social Security, but also the pensions, retirement accounts, asset income and SSI that sit beside it. The parity ledger lists those as three missing capabilities (`docs/parity-ledger.md:90, 129, 130`). This design prices the work that would make each one testable, and then comparable with DYNASIM's and MINT's published income tables.

It follows Track B's rules (Track B §1, §5.1):

- Each mechanism, population and horizon is admitted separately, and only through a registered gate against independent observations.
- No DYNASIM or MINT comparison may select structure, parameters, denominators or rows. Agreement with DYNASIM or MINT never rescues a failed gate.
- Source hashes, populations, estimands, tolerances and alternatives are frozen before any real-data outcome is computed.
- Every milestone reports its verification class and admitted scope (§4.2).

Two facts shape the plan. First, the lane's first admissions can be gated on PSID, survey and SSA data now, without waiting for Track B's forward-earnings successor: their gates score histories and held-out waves the data already hold. Second, nothing in this lane can enter a 2030 projection, close an SSA-caseload check, or support a projected comparison with DYNASIM or MINT until Track B's chain (H, I, B4, J, B7) and a representative starting population exist. The milestones fall into two tiers that follow those two facts (§4.3). The one exception to the second fact is C1's arm (a), which compares outcomes the PSID recorded, not projections, with DYNASIM3's published tables. A third fact overrides both for now: PSID's conditions of use, as revised between August and October 2026, prohibit AI and LLM use with PSID data, so every PSID milestone waits on Max's ruling (d1899, §2.7).

## 2. What exists now

Every citation in this section was read in this run at master `1e739d32`, unless it names another revision.

### 2.1 Covered earnings

- **No split exists.** The projections and the Axiom bridge treat all PSID labor income as covered (`docs/parity-ledger.md:90`).
- **A correction design exists, and stopped.** `docs/design/covered_earnings_correction.md` is 56,304 lines (4.0 MB): a base design in §§1–14 and nineteen appended amendments in §§15–33. Its charter classifies each person-year source component as `covered_wage`, `covered_self_employment`, `noncovered` or `unresolved` (§1, lines 30–34), with a frozen statutory ordering in which wages consume the taxable maximum first and self-employment only the remainder (§3.2, lines 286–321). Amendment 1 removed a required SSA covered-share target that no publication supplies (§15.2, lines 8185–8199). Amendment 2 added a deterministic, fitting-free correction path (§16.1, lines 9193–9220). Issue #403 records a law-gap sweep at revision 21 that found nine further seams. PR #405, Amendment 20, closed unmerged on 25 September 2026, and the ledger records that the campaign stopped on 9 September.
- **Pieces of it are code.** `src/populace_dynamics/data/historical_coverage_rule_validation.py` validates the syntax of legal-rule rows and defers everything that needs a ratified inventory (lines 1–9). Its fact vocabulary names Section 218 groups and positions, public-retirement-system participation, federal service and retirement systems, railroad service, ministerial and religious-order service and exemptions, domestic, agricultural, election, family and casual service, and student service with an employer-school nexus (lines 80–101). `src/populace_dynamics/data/psid_covered_earnings_registry.py` freezes the PSID reference-year map and exposes a fail-closed boundary instead of an official crosswalk (lines 1–11). `src/populace_dynamics/covered_wage_history.py` attaches declared covered-wage observations to a history and "never infers wages from labor income" (lines 1–6).
- **The PSID job context is read for 2003–2023 only.** `src/populace_dynamics/data/psid_job_context.py` emits raw, uninterpreted tokens (lines 1–8) for occupation, industry, self-employment, incorporation, the government-employer item (`BC24`/`DE24 WORK FOR GOVT?`) and state, for interview waves 2003–2023 (`psid_job_context_registry.py:33, 270–320`). No value code of the government item has been adjudicated.
- **SSA's earnings file is staged.** `src/populace_dynamics/data/epuf.py` reads the 2006 EPUF, a 1 percent sample of SSNs with capped taxable earnings, covered wages plus covered self-employment, for 1951–2006, byte-pinned (lines 1–43). EPUF carries birth year and sex but no state, sector or employer (lines 9–19).
- **A gate on EPUF has already failed to lock.** `gate_epuf` scored the gate-1 generator's earnings against EPUF on 1998–2004 and closed without locking: "it has not been shown to catch anything gate 1 does not already catch, and it could not meet its own check on its bite" (`docs/amendments/gate_epuf_registration_proposal.md`, "Outcome, in plain words"). Its floors and bridges between PSID earnings and EPUF are committed (`runs/epuf_gate_floors_v1.json`). `gate_epuf_fill` later used EPUF to certify career fills (`docs/parity-ledger.md:89`).

### 2.2 Wealth, pensions and other income

- **Reported wealth, waves 2005–2013.** `src/populace_dynamics/data/family_income.py` reads label-verified family income and WEALTH1 for the 2005, 2007, 2009, 2011 and 2013 waves (lines 1–30). From 2009 the family file carries the wealth composites; for 2005 and 2007 it reads the PSID wealth supplements, which Max downloaded and staged under decision d189 (lines 52–77). Only those two supplements are staged (`~/PolicyEngine/psid-data/wealth/`: 2005, 2007). The PSID family files for every wave from 1968 to 2023 are staged (`~/PolicyEngine/psid-data/family/`).
- **Employer DC balances, waves 2005–2013.** `src/populace_dynamics/data/employer_dc.py` reads the pension section's current-job and previous-employer account balances for head and wife, following the questionnaires' routing item by item (lines 1–110). It also documents the section's plan-type items (DB formula, DC account, both) and the expected-benefit item `P62`.
- **One static use.** Exercise 2 annuitizes 80 percent of WEALTH1 (optionally plus employer DC balances) into a level real annuity at 3 percent, priced on the NCHS 2000 life tables, joint and 50 percent survivor on the family head and spouse (`src/populace_dynamics/estimates/adjusted_poverty.py:49–70, 404–426, 851–912, 1340–1397, 1553–1559`). It replaces reported asset income with that annuity (`:22–38, 1560–1573`).
- **Lifetime-earnings groups exist as code.** `src/populace_dynamics/estimates/lifetime_measures.py` computes MINT8's three lifetime measures, the initial AIME quintile at 62 and the own and shared lifetime payroll-tax quintiles, from careers of labor earnings, with every undocumented choice a registered builder default (lines 1–45).
- **Microcosm's frame carries wealth and pension income, but not every piece, and not on the right people.** The Microcosm-start plan maps the frame's variables (`docs/plans/microcosm-start.md:269–284`): household `net_worth` from a QRF anchored on the SCF 2022; liquid assets (`bank_account_assets`, `stock_assets`, `bond_assets`); DB pension income from the 2015 IRS file; retirement-account withdrawals; asset income. It has **no employer DC balance, no DB coverage and no home value** (`:282`). Microcosm#1215 (open) finds that each household's liquid assets sit wholly on its lowest-line member, against the stage's declared head carry, and that everyone outside that member's marital unit therefore holds $0 countable resources by construction; its proposed real fix is a new draw and allocation unit, validated against SCF and SIPP totals and refitted.
- **A first ageing rule is proposed, not built.** The Microcosm-start plan's §2.3 (lines 286–302) ages each income and wealth item by keeping each unit's rank within its sex, age-band and household-type cell, with a report-only check, A1, against the PSID's wealth panels. Its tasks T3 (PSID wealth readers for 1999–2021, 4–6 agent-days) and T10 (the table, the rule and A1, 6–10) are priced there (`:414, 421`). The plan's registration waits on d947, which is parked.
- **A Form 5500 reader is in review.** PR #386 (open, last updated 24 August 2026) adds readers for DOL Form 5500 plan-sponsor filings and OSHA establishment summaries. It is unmerged.
- **Nothing projects wealth, pensions or asset income** (`docs/parity-ledger.md:130`).

### 2.3 SSI

- **A static offset.** Exercise 2's primary rule raises each baseline SSI recipient's SSI by the fall in countable Social Security income after the $20 general exclusion, capped so SSI stays at or below the FBR, and enrolls no one (`adjusted_poverty.py:96–106, 1420–1449`; Max's ruling d189). A registered alternative also enrolls head/wife units the cut makes income-eligible and whose WEALTH1 less vehicles passes the resource limit (`:1450–1475`). Federal SSI only; its parameters are a pinned capture from PE-US (`:199–204, 1085–1122`).
- **Registration 19.** `docs/design/pe_us_depletion_cut_population.md` (ratified `sa1-ratified-1`) ran PE-US 2.18.0's SSI on Microcosm's 2024 frame, static and report-only, with imputed liquid assets (§§1–2), code merged in #511 (`src/populace_dynamics/bridge/depletion_cut_population*.py`). Its §4 reads PE-US's SSI encoding: countable resources are exactly bank, stock and bond assets; the $2,000 and $3,000 limits are not indexed; 2.18.0 deems an ineligible spouse's and parent's income but not their resources; and its spousal-deeming cap differs from 20 CFR 416.1163(e)(2) (§4.1, §12 items 3 and 12).
- **The bridge's person inputs are narrow.** `src/populace_dynamics/bridge/policyengine_us.py` passes Social Security by type, employment income, taxable private pension income, interest income, bank-account assets and rent (`:225–236, 278–291`). It passes no stock or bond assets, no self-employment income, no disability, blindness or immigration status and no retirement-account balance. It runs PE-US in a separate interpreter, pinned by default to 2.18.0 (`:128–132`), and accepts parameter overrides per run (`RunCase.parameter_overrides`, `:810–818`).
- **Nothing projects SSI.** The engine's eight modules include no SSI step (`docs/parity-ledger.md:108`; `src/populace_dynamics/engine/loop.py`).

### 2.4 PolicyEngine-US, policyengine.py and Axiom, checked in this run

- **PE-US 2.18.0** (the bridge's pin; installed at `~/.venvs/policyengine-us-2.18.0`) has federal SSI with income deeming from an ineligible spouse and parent, in-kind support and maintenance, living arrangements including the one-third reduction, and couple computation (`variables/gov/ssa/ssi/`, `ssi_amount_if_eligible.py`). Files whose names contain `state_supplement` exist for six states: CA, CO, MA, NM, SC and TX. SSI2 inventories other encodings, and the release SSI0 selects, separately.
- **What PE-US needs to decide eligibility.** `is_ssi_eligible` is monthly and requires ABD status, the resource test, and citizenship or qualified-noncitizen status (`is_ssi_eligible.py:8–18`); qualified-noncitizen status reads `immigration_status` and, for permanent residents, qualifying quarters of earnings (`eligibility/status/is_ssi_qualified_noncitizen.py:12–38`). Earned income counts employment and self-employment income (`parameters/gov/ssa/ssi/income/sources/earned.yaml`); unearned income counts fifteen named sources, among them pensions, Social Security, veterans' and survivor benefits, retirement distributions, alimony and child support, dividends, interest and rents (`unearned.yaml`).
- **PE-US annualizes.** Its income exclusions convert annual income to monthly in equal twelfths, apply the monthly exclusions, and convert back (`eligibility/income/_apply_ssi_exclusions.py:18–23`), and a couple's countable income is divided between the two members when both are eligible (`eligibility/income/ssi_countable_income.py:79–85`).
- **PE-US 2.53.1**, the latest release on PyPI on 21 October 2026 (wheel SHA-256 `fc5cd5c4…d8d8`), adds resource deeming from an ineligible spouse and parent (`variables/gov/ssa/ssi/eligibility/resources/deemed/`). Its countable-resource list is unchanged: bank, stock and bond assets only, with the note "Excludes home, one vehicle, household goods, burial plots, and retirement accounts" (`parameters/gov/ssa/ssi/eligibility/resources/countable.yaml`). Those files are preserved, with the wheel's hash, in `EV/income-resources-20261021/sources/peus-2.53.1/`. Microcosm#1215 dates the change to policyengine-us#10040, merged 11 October 2026; this design has not opened that PR.
- **policyengine.py 6.10.0**, the latest release on PyPI on 22 October 2026 (uploaded 21 October), pins `policyengine-us==2.2.1` in its `us` extra (PyPI metadata). PE-US 2.2.1 was uploaded on 15 September 2026, before 2.18.0 (30 September), and predates the resource-deeming change. Its federal SSI trees match 2.18.0's: every file under `variables/gov/ssa/ssi/` and `parameters/gov/ssa/ssi/` has the same path in both releases, 78 of the 79 are byte-identical, and the 79th, a README, differs by one trailing blank line; files whose names contain `state_supplement` cover the same six states (`EV/income-resources-20261021/sources/peus-2.2.1-vs-2.18.0-ssi.md`). Files outside those two trees, among them immigration status, the income variables and other state programs, were not compared. SSI0 inventories 2.2.1's whole SSI chain against the input contract before any SSI computation, and any capability present in 2.18.0 but absent in 2.2.1 is refused and counted under `RULES_ENGINE_GAP`.
- **PE-US excludes retirement accounts; SSA counts some of them.** POMS SI 01120.210 (captured 2026-10-21) says a retirement fund owned by an eligible individual "is a resource if he/she has the option of withdrawing a lump sum," even if the person is not eligible for periodic payments; that if the person is eligible for periodic payments the fund may not be a countable resource; that a fund is not a resource if the person must leave the job to get any payment; that its value is what can be withdrawn after any early-withdrawal penalty, with taxes not deducted; that a person eligible for periodic retirement benefits must apply for them, and must choose periodic benefits over a lump sum where offered; and that an ineligible spouse's or parent's retirement fund is excluded from deeming (§§A.3, B, C.1, E.1, E.4). Treating these correctly needs each account's access and periodic-payment status, not only its balance.
- **Axiom.** `rulespec-us` at origin/main `5796861e5` (20 October 2026) encodes parts of the SSI statute: 42 U.S.C. 1382(a)(1)–(3), 1382(b), 1382(e)(1), 1382a(b)(2), 1382a(b)(4), 1382b(a), 1382c(a)(1)–(2), 1382f(a) and 1382f(c). It encodes no 20 CFR part 416 regulation. Differential checks against it are possible for those sections only.
- **PolicyEngine's interface rule is a mandate.** PolicyEngine's guidelines say to "Build analyses and integrations against policyengine.py, latest — never against policyengine_us internals" (`~/PolicyEngine/CLAUDE.md:10–12`), and to mirror every PE-US policy fix in rulespec-us in the same piece of work. The existing bridge predates this lane; new integration here follows the rule unless Max grants an exception (decision 6, §12).

### 2.5 Legal facts the design relies on, checked in this run

Captures are in `EV/income-resources-20261021/sources/`, listed with their hashes in `MANIFEST.md`.

- **The RET counts noncovered wages.** 42 U.S.C. 403(f)(5)(C) deems services that are not covered employment, performed in the United States as an employee, to be employment for the earnings test, and excludes from wages any payment "on account of retirement." So earnings-test earnings are not covered earnings, and pension income does not count toward the test.
- **The windfall elimination provision and the government pension offset are repealed** for benefits payable for months after December 2023 (Public Law 118-273, approved 5 January 2025). Noncovered pensions no longer reduce projected benefits; they still mattered for benefits paid before 2024.
- **SSI's benefit rates are indexed and its resource limits are not.** 42 U.S.C. 1382f(a) raises the FBR amounts by the Social Security COLA, applied to the unrounded prior amount and rounded to the next lower multiple of $12 a year. It indexes the benefit-rate subsections of §1382 and not the resource limit.
- **Coverage exclusions** (42 U.S.C. 410(a)): federal service by a person continuously in excluded service since 31 December 1983 (§410(a)(5)); state and local government service, except under a §418 agreement and except, under §410(a)(7)(F), service by a person who is not a member of the employer's retirement system, for service performed after 1 July 1991 (Pub. L. 101-508 §11332(d), as the section's notes record); ministers' and religious-order members' service, which is excluded from employment (§410(a)(8)(A)) but covered as self-employment unless a 26 U.S.C. 1402(e) exemption is in effect or a vow of poverty applies (42 U.S.C. 411(c)(4) and the sentence that closes §411(c)); employees of an electing church (§410(a)(8)(B)), whose church employee income is covered with a $100 threshold in place of $400 (§411(i)(2)(B)); railroad employment (§410(a)(9)); students working for their school (§410(a)(10)); and family and domestic employment of the kinds §410(a)(3) lists. Net earnings from self-employment below $400 are not self-employment income (42 U.S.C. 411(b)(2)). This list is not exhaustive; the cash-pay thresholds for domestic, agricultural and election work are CE1 research items.
- **Retirement-plan rules.** The RMD "applicable age" is 73 for a person who attains 72 after 2022 and 73 before 2033, and 75 for a person who attains 74 after 2032 (26 U.S.C. 401(a)(9)(C)(v)); the two clauses overlap for people born in 1959, which WP2 resolves from IRS guidance. Early distributions bear a 10 percent additional tax on their includible portion (26 U.S.C. 72(t)(1)). Elective deferrals and DC annual additions are capped (26 U.S.C. 402(g)(1), 415(c)(1)).
- **Open research questions, not claims.** The RMD ages in force before 2023 (they bear on the proposed 2017–2023 holdout), the cost-of-living rules of federal and state DB plans, and the history of each coverage rule before its current text are not yet read. CE1 and WP2 read them before use.

### 2.6 What the coordinator priced

The coordinator's forecast, revision 2 of 22 October (`EV/coordinator/parity-forecast-20261021.md:89–91`), lists as its own order-of-magnitude estimates covered and noncovered earnings at 8–12 engineer-days, SSI in the projection at 10–20, and wealth, pensions and other income at 30–60. No design priced them. Its stress test assumes five of eight later milestones need a second attempt, "a stress assumption, not a rate" (`:76`); the gate record it cites is that four of the seven locked passing gates needed an amendment after an earlier failure, with `gate_epuf_fill` and B2 recorded separately (`:38`). §4.4 sets this design's figures beside the coordinator's.

### 2.7 PSID's conditions of use now prohibit AI and LLM use with PSID data

PSID's live Conditions of Use (https://simba.isr.umich.edu/U/CondUse.aspx, read 2026-10-23) say: "The use of Artificial Intelligence (AI) programs and Large Language Models (LLMs)- in conjunction with PSID data is strictly prohibited. This restriction is in place to protect the confidentiality of PSID respondents. It also ensures that we can document use, as required by our funders." The same revision drops the earlier exception that let a registrant pass data to "assistants or students you supervise during an ongoing project".

- **When it appeared.** Every Internet Archive capture of the page through 13 August 2026 lacks the clause; the 15 October 2026 capture has it. The project's PSID files were downloaded under Max's registered account on 3 July 2026 (`~/PolicyEngine/psid-data/README.md`).
- **Evidence.** The live text and both archive captures, with hashes, are in `EV/income-resources-20261021/sources/psid-conditions/`. The lane's source catalog surfaced the clause; the author confirmed it on the live page.
- **What it blocks here.** Every milestone in this design that reads PSID data is built and run by AI agents: D1, CE2–CE5, WP1 and WP3–WP6, SSI4, SSI5 and SSI5R, and C1's arm (a). Whether and how the clause applies to a registration made before it appeared, and to agent-written code that computes registered aggregates, is not this design's call.
- **Queued.** Decision d1899 (security priority, no default) asks Max whether to pause agent-run PSID work and ask PSID (psidhelp@umich.edu) how the clause applies. It bears on every PSID-based design in the project, not only this one.
- **If the answer forbids agent use**, this lane's PSID gates cannot run as designed. The lane would return with a redesign on sources whose terms allow it (SIPP, the SCF, EPUF and SSA's tables, each with its own terms checked) or with human-run registered steps, and a new price.

## 3. Design

### 3.1 Covered earnings: a lean successor to the correction campaign

**Recommendation (decision 1, §12):** retire the 56,304-line correction design as a campaign, keep its estimands, and build a short successor, CE v2.

The old design's substance is sound and is kept: the four statuses; the rule that unresolved earnings are never silently counted as covered; wage-first cap coordination, with no self-employment loss offsetting wages (§3.2 of that design); one ledger that both benefits and revenue read (§3.3); the "frame-relative" label; and Amendment 2's fitting-free path, which fits nothing to official totals. What is dropped is the ceremony that surrounds it: exact-dyadic encodings, nested ratification oracles and the amendment layers that the #403 sweep found would each cost another stop-and-cure round.

**CE v2, in four parts.**

1. **A coverage-rule registry** (CE1). Each rule has effective dates and a citation, starting from the exclusions in §2.5 and the existing registry's fact vocabulary (§2.1), and adding each rule's history before its current text. Each rule carries worked examples from SSA's published guidance. This is statutory conformance; it uses no PSID data.
2. **A PSID job-context crosswalk for 1968–2001** (CE2). It extends the existing 2003–2023 reader to the earlier waves and adjudicates the value codes of the government-employer, industry, occupation, self-employment, incorporation and state items in every wave, with the repository's label-verification discipline.
3. **A classifier** (CE3). It classifies earnings as covered only after resolving every applicable exclusion; otherwise it keeps them `unresolved`. Where the data identify an exclusion's facts, the rule decides it. Where they do not, chiefly for state and local government workers, the classifier assigns a probability of noncoverage from aggregate sources by state, occupation group and era, and leaves the remainder `unresolved`. No annual series of noncovered state and local employment was found (catalog §23); the candidate sources are Census's Annual Survey of Public Pensions membership by state, SSA's Section 218 coverage references, and, if D5 is admitted, the Synthetic Beta's noncovered earnings. Where none supports a state's prior, those earnings stay `unresolved`. It fits nothing to the SSA totals it is later checked against.
4. **A registered gate, CE-G** (CE4). It scores PSID-corrected careers against EPUF by birth cohort, sex and age band for 1968–2006: the share of person-years with positive covered earnings, capped covered-earnings quantiles, and years without covered earnings. Because EPUF has no state or sector, noncoverage is diluted in those cells, and `gate_epuf` failed its own bite check on a shorter overlap (§2.1). So IR0 also judges, on planning values, two more cell families:
   - **by state:** covered workers and taxable earnings by state against SSA's Annual Statistical Supplement Table 4.B10 (catalog §11), where the PSID's state item gives the classifier's noncoverage its bite;
   - **by administrative noncovered earnings:** the SIPP Synthetic Beta, version 7, carries detailed-earnings-record covered and noncovered earnings for 1978–2014 (`total_der_fica_YYYY`, `total_der_nonfica_YYYY`), with results validated on the confidential Gold Standard File by Census staff (catalog §5; D5). It is the only source found that measures noncovered earnings directly.

   **The bite check comes in this order:** IR0 freezes CE-G's cells, tolerance rule, pass conjunction and bite rule. CE4 drafts the block, takes it through two referee rounds and packages the registration for #42. Only after the registration pins its commit does CE4 build the truth-only floor and then, before any CE v2 output is scored, score the all-covered proxy against it, as B2's floor was built after B2's registration (`track_b/README.md:133–134`). If the proxy passes the cells CE v2 claims to fix, the gate stops as `WEAK_POWER_OR_VACUITY` and is rescoped prospectively under a new registration. The proxy's result is recorded as exposure. SSA's national covered-worker and taxable-earnings totals (Annual Statistical Supplement section 4) are reported beside it, frame-relative, until a representative population exists.

**What CE v2 hands on** (CE5): one person-year table for 1968 onward with labor earnings, covered wages, covered self-employment, noncovered earnings, unresolved earnings, RET-countable earnings (covered plus noncovered wages plus net self-employment earnings, per 42 U.S.C. 403(f)(5)) and the status probabilities, with provenance. AIME and the lifetime-earnings groups use the capped covered channels. The earnings test uses the RET-countable channel. National payroll (Registration 18, M7) uses capped covered payroll.

**Projected years.** The forward-earnings law has no job identity, so a projected year cannot be reclassified from a new job. The first version carries each person's last observed coverage status forward. A proposed registered sensitivity treats all projected wages as covered. A reset conditioned on a job change waits for a separately sourced, priced and admitted job process, which no plan contains. The choice of sensitivity is Max's (decision 8, §12).

### 3.2 Wealth and pensions: a null, a donor model and a structural option

Three model tiers, each a registered candidate, each scored by the same gate:

- **M0, the null.** The Microcosm-start plan's rank-preserving rule (§2.3 of that plan): each unit keeps its rank within its cell and takes that rank's value from the start-year cross-section as it ages. It is the baseline any candidate must beat, and its known flaw (it uses the cross-section's age profile as each cohort's future, which overstates DB pensions for younger cohorts; `microcosm-start.md:296`) is what the gate's bite check targets.
- **M1, donor trajectories (the proposed candidate).** At each projected wave, match each unit to PSID donors on age, sex, marital state, household income rank, net-worth rank and pension state, and carry the donor's transition between two consecutive waves, both at or before the boundary: its change in ranks and its pension-state transition. This is the idea that passed gate 1 for earnings histories (rank-based donors; `docs/plans/microcosm-start.md:132–142`), where a QRF chain that forgot each person's history failed. The state it carries: net worth and its components (liquid assets, retirement accounts, home equity, other assets, debt); DB coverage on the current job, vesting and receipt; DC participation and balance; each retirement account's access and periodic-payment status; pension benefit amounts; withdrawals from retirement accounts; and asset income. Events change ranks by rule: a surviving spouse keeps the household's assets, a divorce splits them by a registered rule, and a death removes them from the population as a recorded exit.
- **M2, structural accumulation (conditional; priced separately as WP7).** Explicit DC contributions within statutory limits, employer match, returns on a named assumption path, leakage at job change, and DB accrual by sector. It is built only if M1 fails its gate, or if a comparison needs saving to respond to a reform. It needs a ruled return assumption (decision 2, §12).

**The rule layer** (WP2) is statutory and shared by all three: RMDs (§2.5); plan early-withdrawal penalties, which set SSI's resource value of a withdrawable account (POMS SI 01120.210 A.3), where whether SSA treats the 26 U.S.C. 72(t) additional tax as such a penalty or as a nondeductible tax is an open question SSI2 settles from SSA guidance; contribution limits; and the conventions of DB plans. The statutory items in §2.5 were read in this run; the historical RMD ages and DB plans' cost-of-living rules are open research questions WP2 settles from their sources before use.

**The gate, WP-G** (WP5), scores M0 and M1 on held-out PSID waves. Proposal, to be frozen at IR0: candidates use information through the 2013 wave; the gate scores the 2017–2023 waves for the 2013 roster on its realized support, so survival and family events are the PSID's own and the gate isolates the wealth and pension law, as gate m6's replay did for earnings (Track B §2, "the replay function"). Its cell families follow the ledger row's test (`docs/parity-ledger.md:130`):

- pension coverage (DB and DC on the current job) and DB benefit receipt and amounts;
- DC and IRA balances, and withdrawals from them;
- asset income, its receipt and amounts;
- net worth and the share whose countable liquid assets sit below SSI's limits;

each by birth cohort and by lifetime-earnings group (`lifetime_measures.py`'s initial AIME quintile at 62, on CE's covered earnings once CE5 passes and on labor earnings, labelled, before), with sex and age bands where power allows. Floors come from household half-samples, as B2's did (`docs/parity-ledger.md:91, 165`). IR0's power audit partitions the cells into gated and report-only before any candidate result. The order follows CE-G's: registration first; after the registration pins its commit, the truth-only floor; then **M0 is scored first**, and if it passes the cells its flaw predicts, WP-G stops as vacuous before M1 is scored. M0's result is recorded as exposure. PSID's 2025 early release (selected wealth content for families interviewed in 2023 and 2025, un-imputed; catalog §1) is a candidate extra held-out wave that IR0 judges. **WP6 supplies evidence only for its registered states, income concepts and cells.** Any ledger requirement whose cells IR0 cannot power stays open, report-only, until a separately priced gate covers it.

**External checks** (WP8) — the SCF 2019 and 2022, the Federal Reserve's Financial Accounts, DOL Form 5500 statistics, IRS SOI IRA tables, SIPP — are report-only and frame-relative until the projection starts from a representative population.

**Output concepts** (WP6). The comparison targets measure income differently from the PSID, so WP6 adds the concepts they use: MINT8's household income sources (Social Security, annuitized asset income from DC plans and savings, DB pension income, earnings, coresident income; MINT8 Table User Guide, committed capture `data/external/mint8_table_user_guide.source.html`) and Butrica and Uccello's annuitized financial assets, which `adjusted_poverty.py` already prices. The annuity code is reused, not copied.

### 3.3 SSI

**Rules come from PE-US through policyengine.py; the projection supplies their inputs.** SSI0 uses the latest policyengine.py. Today that release certifies PE-US 2.2.1 (§2.4), which predates resource deeming. Configurations that need resource deeming are refused and counted until a policyengine.py release certifies a PE-US that has it, unless Max grants an exception to pin PE-US directly (decision 6). Retaining direct PE-US internals in new work requires that exception, with its scope recorded.

**SSI0 publishes a complete source-to-input contract** before any SSI computation. It maps every input PE-US's SSI chain reads to a source in each starting population (PSID, SIPP, Microcosm's frame), or to an explicit, registered assumption, or to a refusal:

- household, marital-unit and tax-unit links, which decide joint claims, deeming and couple computation;
- ABD status, blindness and the SSI disability criteria;
- immigration status and, for permanent residents, qualifying quarters (§2.4);
- every earned and unearned income source on PE-US's lists, self-employment included;
- resource ownership by person and marital unit, never one household vector on one person (microcosm#1215);
- each retirement account's balance, lump-sum access and periodic-payment eligibility (POMS SI 01120.210);
- living-arrangement and in-kind-support inputs;
- take-up.

A missing input refuses the case or applies a registered assumption; it never defaults silently to a PE-US default.

**Parameters past the last realized year** (SSI1) follow the statute: the FBR by 42 U.S.C. 1382f(a) on the projection's COLA path, the resource limits and income exclusions fixed in nominal dollars, and state supplements frozen at the last realized year, a named assumption.

**Conformance before population** (SSI2, gate SSI-C). Worked examples from POMS and 20 CFR part 416: income exclusions, earned income, spousal and parental deeming including the 416.1163(e)(2) cap, couple computation, living arrangements and in-kind support, citizenship and qualified-noncitizen status, and retirement funds: lump-sum access, the periodic-payment requirement, and valuation after withdrawal penalties with taxes treated separately. Differential checks run against rulespec-us where it encodes the section and against exercise 2's static offset as a special case. Configurations PE-US gets wrong are refused and counted, never dropped from denominators, as G does. Each PE-US discrepancy is filed upstream with its rulespec-us mirror, under PolicyEngine's mirror rule.

**First admission covers the aged** (SSI3). People 65 and over are categorically eligible by age. Blind and disabled adults need a disability determination that does not depend on insured status, which the engine lacks: its DI awards never check insured status and are fitted to data through 2008 (`docs/parity-ledger.md:98`). They are flagged unsupported and stay in denominators. SSI7 adds them after Track B's B4 and the insured-status rule the rules lane now owns (`parity-forecast-20261021.md:49, 95`). It extends SSI4's take-up to blind and disabled adults, and its gate against SSA's blind and disabled caseloads also needs SSI9's timing and a representative start, as SSI8 does. SSI7 is in the base: the ledger's test asks for participation "by age and type" (`docs/parity-ledger.md:129`).

**Timing.** SSI is a monthly program; PE-US's eligibility is monthly, but its income tests divide annual income into equal twelfths (§2.4). So the lane's initial SSI estimands are **annualized potential benefits under a frozen annual state**, with registered assumptions on the timing of income and resources (equal twelfths, resources at their annual value). Actual December receipt, annual payments and caseloads remain blocked until a timing gate passes (SSI9, on SIPP's monthly records and Track B's I).

**Take-up is estimated, not aligned** (SSI4). Take-up is modelled on SIPP and PSID units under the frozen-annual-state eligibility above, as a function of potential benefit, age, sex, marital state, Social Security receipt and living arrangement, and fitted only on the training partition IR0 freezes. Survey misreporting of SSI as Social Security is a named limitation. Aligning to SSA's caseloads instead would be a methodology choice the engine has not made (`docs/parity-ledger.md:112`).

**The gate, SSI-G** (SSI5): the aged's annual-state receipt propensity, the share reporting SSI receipt by age band, sex and marital state, against the model's take-up times frozen-state potential eligibility, in held-out PSID waves and a held-out SIPP panel. Its payment estimand is consistent with that choice: potential annualized benefit among reporting recipients against their reported amounts is a report-only diagnostic, not a gated cell. Its bite null is a take-up model on age and sex only. After the registration pins its commit and the truth-only floor is built, the null is scored before SSI4's model; if it passes the cells SSI4 claims to fix, SSI-G stops as vacuous. SSI5 builds and registers the gate, then builds the floor and scores the null; SSI5R runs the model once and publishes. Together they supply held-out survey evidence only.

**Against SSA's caseloads** (SSI8): aged December caseloads by age on a representative start, against SSA's published counts for a year after the frame's calibration year (the frame is calibrated to SSI dollars and to SSI recipients by state and age group for December 2024; `pe_us_depletion_cut_population.md` §2.3), with numerical limits and uncertainty frozen at IR0. It needs SSI9 and a representative start. Because the frame's take-up flag already comes from CPS reports and SSA counts (`microcosm-start.md:273`), a model that carried the frame's calibrated receipt forward could pass without testing anything. So on a Microcosm start, SSI6 and SSI8 replace the frame's `takes_up_ssi_if_eligible` with SSI4's model and never read the frame's reported SSI. IR0 freezes the rule: the minimum gap between SSI8's year and the frame's calibration year, and the carried-calibration null. SSI8's record is completed for the certified frame's calibration year before SSI8 registers, and SSI8 shows the null failing before the model is scored. Validation by type also needs SSI7.

**Inside the projection** (SSI6): each projected year runs through PE-US with Social Security from the engine, resources, pensions and asset income from WP, and earnings from Track B once admitted. It reports annualized potential SSI and the potential poverty effect of a Social Security cut, frame-relative. **Projected caseloads and payments** (SSI6b), and the poverty effect of a Social Security cut on them, follow only after SSI8 and SSI9 pass on a representative start, using SSI4's take-up and SSI9's timing, and only for the cells those gates admit: aged cells after SSI8, and blind and disabled cells after SSI7.

### 3.4 Other income

Veterans' benefits, unemployment and workers' compensation, child support, alimony and coresident income are carried from the starting population by M0's rank rule and are not gated in this design. A target that needs them gated says so in its scope matrix (Track B §3.4, B7).

### 3.5 Comparisons with DYNASIM and MINT

Comparisons come after the gates and are never validation (Track B §3.2, B7). Each is a registered one-shot under Track B §5.4's B7 requirements: a sealed comparator with two transcriptions, a blind builder under an updated `RESTRICTED-FILES.md`, a hashed forecast before the run, and a one-shot at a registered commit with the seal opened after the artifact commit. §6 names the targets.

A projected comparison needs Track B's whole chain: C1's arm (b), C2 and C3 depend on SSI6, WP-G, SSI-G, B3L, B4, J and every prerequisite in the target's B7 scope matrix. C1's arm (b) may itself serve as a B7 target if it is selected and registered as one. National claims need a representative start; a PSID-cohort comparison stays frame-relative. **C1's arm (a) is exempt**: it compares outcomes the PSID recorded, in the comparator's income concept, with DYNASIM3's projections, as U2 does for poverty, and projects nothing.

## 4. Milestones

### 4.1 Milestone table

The row marked † is conditional and is excluded from the totals in §4.3. Tier 1 rows can start on approval; tier 2 rows wait on Track B or a representative start. Every row that reads PSID data (D1, CE2–CE5, WP1, WP3–WP6, SSI4, SSI5, SSI5R and C1's arm (a)) also waits on d1899 (§2.7). Rows that compute or publish PSID statistics (CE4, CE5, WP5, WP6, SSI5, SSI5R and C1) follow §7.2's U2 sequencing rule. In every gate row, registration on #42 comes before the floor, and the floor before the bite null and the candidate.

| Id | Tier | Deliverable | Verification or gate | Effort estimate (d / lw) | Depends on | Unlocks |
|---|---|---|---|---|---|---|
| **IR0** | 1 | Source, exposure, access and power audit for every gate in this lane: CE-G (including the bite demonstration and the state cell family), WP-G, SSI-G, SSI8, SSI9, and the target definitions of C1–C3 | A written record per gate freezes Track B §5.2's ten elements and the named power procedure before that gate registers. It records exposure already on file (§7.2). A blinded review checks feasibility and power | 6–9 / 1.5–2.25 | D1, D2, D4 and D5 (sources to audit); B0.2's protocol (PR #554) if frozen, otherwise IR0's own, frozen at its start | Registration of CE-G, WP-G, SSI-G; SSI4's training partition |
| **D1** | 1 | PSID income, wealth and pension readers: wealth supplements 1984, 1989, 1994, 1999, 2001 and 2003 (not staged; PSID Data Center, Max's registered account); family-file wealth 2015–2023; pension-section items outside 2005–2013, including plan type, receipt, amounts and account access; SSI, pension, retirement-withdrawal and asset-income items for every wave used; all label-verified as `family_income.py` is | Exact labels at read time; reconciliation of WEALTH1 with its components; refusal of unstaged or unadjudicated files; tests on invented files | 10–14 / 2.5–3.5 | Wealth-supplement download | WP1, WP3, SSI4, IR0 |
| **D2** | 1 | SIPP readers for the 2018–2025 releases (reference years 2017–2024; catalog §4): monthly SSI and OASDI receipt and amounts, assets and debts, retirement accounts, pension coverage and income (employer-plan offer and participation from the 2021 interview), disability, citizenship, living arrangement. Variables verified against the Census SIPP API as `sipp_jobs.py` does | Label checks against the API; structure-only tests; refusal of unverified years | 5–8 / 1.25–2 | None | SSI4, SSI9, WP8, IR0 |
| **D3** | 1 | SCF reader, 2019, 2022 and 2025 (released 9 October 2026; catalog §6): retirement accounts, DB coverage, net worth, with implicates and replicate weights. No tier-1 gate uses it, so it runs after IR0 | Codebook label checks; implicate handling tested on invented data | 3–4 / 0.75–1 | None | WP8 |
| **D4** | 1 | Pinned captures and parsers for aggregate tables (catalog §§11–23): SSA Annual Statistical Supplement Tables 4.B1, 4.B2, 4.B10 and 4.B11, SSI Tables 7.A–7.E and concurrent-receipt Table 3.C6; SSI Annual Statistical Report (2025 edition and its erratum); SSI Recipients by State and County; POMS SI 01415's annual state-supplement parameters (State Assistance Programs for SSI Recipients ended with its January 2011 edition); SSA's Section 218 coverage references; Census Annual Survey of Public Pensions; Federal Reserve Financial Accounts pension and household tables under their June 2026 codes; DOL Private Pension Plan Bulletin; IRS SOI IRA tables; BLS NCS benefits | Each capture hashed, with URL and retrieval time; parsers print structure only before registration; no Trustees Report cost table | 4–7 / 1–1.75 | None | CE3, CE4, IR0, SSI2 (state-supplement cases), SSI8, WP8 |
| **D5** | 1 | SIPP Synthetic Beta, version 7: application, terms check, reader and cell specification for detailed-earnings-record covered and noncovered earnings, 1978–2014, with the Gold Standard File validation route (catalog §5) | Codebook label checks; the terms check recorded; refusal of unvalidated synthetic results as gate truth | 3–5 / 0.75–1.25 | None (runs on the CE lane after CE0) | IR0's CE-G record; CE4 |
| **CE0** | 1 | CE v2 design note, successor to `covered_earnings_correction.md`, after Max's ruling on the campaign (decision 1) | One review round; nothing registered | 2–4 / 0.5–1 | Decision 1 | CE1, CE2 |
| **CE1** | 1 | Coverage-rule registry with effective dates, citations, rule histories and worked examples (§3.1, part 1) | Statutory conformance on worked examples; refusal of a year with no rule | 4–6 / 1–1.5 | CE0 | CE3 |
| **CE2** | 1 | PSID job-context crosswalk for 1968–2001, and value-code adjudication of the government, industry, occupation, self-employment, incorporation and state items in every wave 1968–2023 | Label verification per wave; raw tokens kept; codes adjudicated against codebooks and setup files | 6–9 / 1.5–2.25 | CE0 | CE3 |
| **CE3** | 1 | Classifier: covered only after every applicable exclusion is resolved; probabilistic state and local noncoverage from D4; the four statuses and the wage-first cap order; invented-data tests | The invariants in §9; property tests | 5–7 / 1.25–1.75 | CE1, CE2, D4 | CE4 |
| **CE4** | 1 | Gate CE-G on EPUF, 1968–2006, plus the state and Synthetic Beta cell families if IR0 finds them powered: block draft; two referee rounds; registration package for #42 (cells, floor procedure, bite rule, pass conjunction); after registration pins the commit, the truth-only floor, then the all-covered proxy scored against it before any CE v2 output (§3.1, part 4) | Registered gate. Section 4 totals report-only | 6–9 / 1.5–2.25 | CE3, IR0, D5 | CE5 |
| **CE5** | 1 | One-shot run, publication, and the person-year handoff table for H, B5, lifetime groups and national payroll | The gate's verdict; the handoff schema's invariants | 2–3 / 0.5–0.75 | CE4 | H's covered channel; B5's RET-countable earnings; WP-G's lifetime groups; Registration 18 and M7 payroll |
| **WP1** | 1 | Starting states: PSID-start wealth components, pension states, account access and periodic-payment states; the Microcosm-start map (shared with Microcosm-start T10's table); requests to Microcosm for DC balances, DB coverage, home value and a corrected resource-ownership contract with rebuilt, validated inputs | Accounting identities; refusal of missing components | 5–7 / 1.25–1.75 | D1 | WP3, WP4 |
| **WP2** | 1 | Retirement-plan rule layer (§3.2), with the open research questions of §2.5 settled from their sources | Statutory conformance on IRS and plan worked examples | 4–6 / 1–1.5 | None | WP4, SSI2 (retirement-fund value) |
| **WP3** | 1 | M0, the rank-preserving null, on the PSID panel, and the report-only check A1 (shared with Microcosm-start T10) | Reproduces the plan's rule on invented panels; A1 report-only | 3–5 / 0.75–1.25 | WP1 | WP5 (as null) |
| **WP4** | 1 | M1, donor trajectories for wealth components, pension states, benefit amounts, withdrawals and asset income, with event rules; built on invented data | The invariants in §9; property tests | 12–18 / 3–4.5 | WP1, WP2 | WP5 |
| **WP5** | 1 | Gate WP-G on held-out PSID waves (§3.2): every cell family by cohort and lifetime-earnings group, partitioned by IR0's power audit; block draft; two referee rounds; registration package; after registration pins the commit, the truth-only floor, then M0 scored before M1 (it must fail the cells its known flaw predicts) | Registered gate | 9–13 / 2.25–3.25 | WP3, WP4, IR0 | WP6 |
| **WP6** | 1 | One-shot run and publication; the output layer of MINT8 and Butrica–Uccello income concepts | The gate's verdict; concept reconciliation tests | 3–5 / 0.75–1.25 | WP5 | SSI6, C1–C3 |
| **SSI0** | 1 | Rules-engine interface through the latest policyengine.py; the source-to-input contract (§3.3); parameter overrides; upstream filing of the retirement-fund gap with its rulespec-us mirror | Interface tests on invented households; the contract's refusal and assumption tests; the pin's source check | 6–9 / 1.5–2.25 | None | SSI1, SSI2 |
| **SSI1** | 1 | SSI parameter projection by 42 U.S.C. 1382f(a), with nominal limits and frozen state supplements | Statutory conformance against SSA's published FBR history; differential against rulespec-us's 1382f encoding | 2–3 / 0.5–0.75 | SSI0 | SSI2, SSI6 |
| **SSI2** | 1 | Gate SSI-C: POMS and CFR worked examples (§3.3), differentials, refused-configuration accounting | Statutory conformance gate, registered | 6–9 / 1.5–2.25 | SSI0, SSI1, WP2, D4 | SSI4 |
| **SSI3** | 1 | Categorical status v1: aged only; blind and disabled adults flagged unsupported | Denominator conservation | 1–2 / 0.25–0.5 | SSI2 | SSI4 |
| **SSI4** | 1 | Take-up model on SIPP and PSID under frozen-annual-state eligibility (§3.3) | Fitted only on the training partition IR0 freezes | 8–12 / 2–3 | SSI3, D1, D2, IR0 | SSI5 |
| **SSI5** | 1 | Gate SSI-G on held-out PSID waves and a held-out SIPP panel: annual-state receipt propensity; payments report-only; power; block draft; two referee rounds; registration package; after registration pins the commit, the truth-only floor, then the age-and-sex take-up null scored before SSI4's model | Registered gate | 6–9 / 1.5–2.25 | SSI4, IR0 | SSI5R |
| **SSI5R** | 1 | One-shot run and publication of SSI-G | The gate's verdict | 2–3 / 0.5–0.75 | SSI5 | SSI6, SSI8 |
| **WP8** | 2 | External checks on a representative population: SCF, Financial Accounts, Form 5500, SOI, SIPP | Report-only, frame-relative | 3–5 / 0.75–1.25 | WP6, D2, D3, D4; a representative start | Report |
| **SSI6** | 2 | SSI inside the projection, each year through PE-US; annualized potential SSI and its potential poverty effect, report-only | Identical-policy equality; Registration 19's identity (§9); report-only | 5–8 / 1.25–2 | SSI5R, WP6; the engine; Track B earnings when admitted | SSI8, SSI6b, C1(b), C2, C3 |
| **SSI9** | 2 | SSI timing gate on SIPP's monthly records: within-year eligibility transitions, December receipt and annual payments, using Track B's I for monthly mechanics | Registered held-out gate; its record frozen at IR0 | 8–12 / 2–3 | SSI5R, D2, Track B's I and its observational timing gate | SSI8, SSI6b; actual-receipt and payment claims |
| **SSI8** | 2 | Aged December caseloads by age on a representative start against SSA's counts for a year far enough after the frame's calibration year; SSI4's take-up replaces the frame's flag; the carried-calibration null must fail first (§3.3) | Registered gate with numerical limits and uncertainty | 4–6 / 1–1.5 | SSI6, SSI9, D4; a representative start | SSI6b; the ledger's SSA-caseload check by age |
| **SSI6b** | 2 | Projected caseloads and payments, and the poverty effect of a Social Security cut on them, with SSI4's take-up and SSI9's timing, on a representative start: aged cells within SSI8's scope, blind and disabled cells within SSI7's | Admitted only within SSI8's, SSI9's and SSI7's scope | 3–5 / 0.75–1.25 | SSI6, SSI8, SSI9, SSI7 | The SSI row's projected-caseload part |
| **SSI7** | 2 | Blind and disabled adults: a disability determination without insured status, shared with DI's process; SSI4's take-up extended to them (3–4 d of the estimate); concurrent receipt | Registered gate against held-out SSA blind and disabled caseloads, with a bite null as SSI-G's | 13–19 / 3.25–4.75 | B4; the rules lane's insured-status rule; SSI5R; SSI9; a representative start | SSI by type; SSI6b's blind and disabled cells |
| **C0** | 2 | Comparator protocol for C1–C3: validation-lane briefs, transcription specifications, values-scan scripts, `RESTRICTED-FILES.md` entries before any builder starts, registration drafts | Review of the briefs; entries made by the orchestrator | 3–5 / 0.75–1.25 | IR0 | C1–C3 |
| **C1** | 2 | DYNASIM3 income and wealth at 67 (Butrica and Uccello 2004): arm (a) PSID-realized outcomes in the comparator's income concept; arm (b) the model projected from the B3L boundary | Registered one-shot comparison. Comparator lane 4–6 d, run and comparison 4–6 d | 8–12 / 2–3 | Arm (a): C0 and WP6's concept layer. Arm (b): also SSI6, WP-G, SSI-G, B3L, B4, J and every prerequisite in the target's B7 scope matrix | The wealth row's DYNASIM comparison, for its cells |
| **C2** | 2 | MINT8 current-law profiles, 2024 and 2030 | Registered one-shot comparison. Comparator 3–5 d, run 3–5 d | 6–10 / 1.5–2.5 | C0, as C1(b); a representative start (d947); an admitted projection to 2030 | MINT cells of the income and group rows |
| **C3** | 2 | Urban's published DYNASIM baseline income of people 62 and older; the comparator lane records which DYNASIM version produced it | Registered one-shot comparison. Comparator 3–5 d, run 3–5 d | 6–10 / 1.5–2.5 | As C2 | DYNASIM cells of the income and group rows |
| **WP7** † | — | M2, structural DC and DB accumulation (§3.2) | Re-scored by WP-G as a new candidate; a new attempt on the ledger | 12–18 / 3–4.5 | WP-G failure or a reform-response need; decision 2 | WP-G retry |

### 4.2 Verification class, admitted scope and the ledger rows each milestone closes

Track B's classes are used unchanged (Track B §3.2), with its "accounting conformance" label for identity checks. Completing an artifact admits nothing empirical by itself; only a registered gate's pass does, within its scope.

| Id | Verification class | Admitted scope on success | Ledger row and the part it closes |
|---|---|---|---|
| IR0 | Source audit | Nothing scientific; authorizes registration of the named gates on the frozen records | None directly |
| D1–D5 | Accounting conformance | Readers for the listed waves, tables and variables only | None directly |
| CE0 | Design review | Nothing | None |
| CE1 | Statutory conformance | Coverage rules for the listed years and categories | Covered earnings: the rule basis |
| CE2 | Accounting conformance | The crosswalk's adjudicated codes only | None directly |
| CE3 | Mechanics (invented data) | Classifier mechanics; no population claim | None directly |
| CE4/CE5 | Held-out prediction where IR0 certifies the cells unused; otherwise retrospective regression (EPUF's 1998–2004 bridge with PSID earnings is already committed, §7.2) | The split for 1968–2006 PSID careers on the registered cells; frame-relative | **Covered earnings: "a covered/noncovered split of PSID earnings" and "a fresh gate on the public-use file"**; the check against SSA's totals stays report-only until a representative population exists |
| WP1 | Accounting conformance | Starting-state construction for the listed sources | None directly |
| WP2 | Statutory conformance | Plan rules for the listed years | None directly |
| WP3 | Report-only (A1) | Nothing admitted | None |
| WP4 | Mechanics (invented data) | M1's mechanics; no population claim | None directly |
| WP5/WP6 | Held-out prediction on waves IR0 certifies unused; otherwise retrospective regression | Only the registered states, income concepts and cells, for the registered roster and waves, on realized support | **Wealth: "first against later PSID waves the model did not see"**, for the cells IR0 powers; the rest stays open |
| WP8 | Report-only | Nothing admitted | Context on a representative population |
| SSI0 | Accounting conformance | The input contract and interface mechanics | None directly |
| SSI1 | Statutory conformance | Projected parameters under the statute's rule | None directly |
| SSI2 | Statutory conformance (registered gate) | SSI computations for supported configurations | **SSI: "eligibility, resource, deeming and state-supplement worked examples"**, for the configurations PE-US supports |
| SSI3 | Accounting conformance | Categorical status for the aged | None directly |
| SSI4 | Model fit on the training partition | Nothing until SSI5 | None directly |
| SSI5 | Gate construction | Nothing until SSI5R | None directly |
| SSI5R | Held-out prediction (survey) | The aged's annual-state receipt propensity on the registered cells | SSI: held-out survey evidence for aged receipt; **SSA caseload validation by age stays open** |
| SSI6 | Accounting conformance plus report-only projections | Mechanics only | None directly (potential SSI only) |
| SSI9 | Held-out prediction (timing) | Within-year SSI timing on the registered SIPP cells | Unblocks actual-receipt and payment estimands |
| SSI8 | Held-out prediction (administrative) | Aged December caseloads by age on a representative start | **SSI: "participation against SSA caseloads by age"** for the aged |
| SSI6b | Projection within admitted scope | Projected caseloads, payments and the poverty effect of a Social Security cut for the cells SSI8, SSI9 and SSI7 admit | **SSI: "projected caseloads, payments and the poverty effect of a Social Security cut"**, for those cells |
| SSI7 | Held-out prediction | Blind and disabled adult SSI | **SSI: participation by type** |
| C0 | Source audit | Nothing scientific | None directly |
| C1 | Registered comparison with DYNASIM3; not validation | Agreement or disagreement on the frozen cells only | **Wealth: "then against DYNASIM's published tables"**, for those cells; poverty and results-by-group rows, for those cells |
| C2, C3 | Registered comparison with MINT8 and Urban's DYNASIM output; not validation | As C1 | Poverty and income distribution; results by group, for their cells |
| WP7 † | Held-out prediction (WP-G re-scored) | M2's registered cells | As WP5/WP6 |

Rows close in full only when every part has its evidence. Covered earnings closes at CE5 except its SSA-totals part, which needs a representative start. Wealth closes after WP6 and C1 for the cells they cover, and stays open for any requirement IR0 cannot power. SSI closes after SSI2, SSI5R, SSI9 (on SIPP), and SSI8, SSI6b and SSI7 (on a representative start).

### 4.3 Totals, lanes and critical path (all estimates)

| Group | Rows | Estimate |
|---|---|---|
| **Tier 1, first admissions** | IR0; D1–D5; CE0–CE5; WP1–WP6; SSI0–SSI5R | **123–186 d (30.75–46.5 lw)** |
| of which: audit | IR0 | 6–9 d |
| of which: data | D1–D5 | 25–38 d |
| of which: covered earnings | CE0–CE5 | 25–38 d |
| of which: wealth and pensions | WP1–WP6 | 36–54 d |
| of which: SSI | SSI0–SSI5R | 31–47 d |
| **Tier 2, projection, caseloads, SSI by type and comparisons** | WP8; SSI6, SSI9, SSI8, SSI6b, SSI7; C0–C3 | **59–92 d (14.75–23 lw)** |
| **Base total** | | **182–278 engineer-days, or 45.5–69.5 lane-weeks** |
| Conditional, not in the base | WP7 | 12–18 d |

Every PSID row in the base waits on d1899 (§2.7); the price assumes the answer lets the design run as written.

**Shared with the Microcosm-start plan.** If d947 proceeds and that plan builds T3, T10 and T12 first, D1 shrinks by about 3–4 d (T3's wealth readers), WP1 and WP3 by about 5–8 d (T10's table, rule and A1), and SSI6 by about 3–5 d (T12's yearly PE-US machinery). Built once for both plans, the base falls to about 171–261 d. This design counts them here because d947 is parked.

**Second attempts, as stress scenarios.** No rate is assumed. The coordinator's forecast stresses its own path with a scenario in which five of eight later milestones need a second attempt, and calls that "a stress assumption, not a rate" (`parity-forecast-20261021.md:76`). For this lane's three empirical gates, a second attempt costs:

| Gate | Repeated work | Retry cost |
|---|---|---|
| CE-G | CE3 rebuilt (5–7); CE4's registration package and two referee rounds (3–5), then, after registration, its floor rebuilt (2–3) and the bite null re-scored (1); CE5's run and publication (2–3); design and review (4) | 17–23 d |
| WP-G | WP4 rebuilt (12–18); WP5's registration package and referee rounds (4–6), then its floor rebuilt (2–4) and M0 re-scored (1); WP6 (3–5); design and review (4) | 26–38 d |
| SSI-G | SSI4 refitted (8–12); SSI5's registration package and referee rounds (3–5), then its floor rebuilt (2–3) and the null re-scored (1); SSI5R's run and publication (2–3); design and review (4) | 20–28 d |

Each retry registers first and then rebuilds its floor, as the coordinator's successor path does ("register, rebuild the floor and score once"; `:62`). A registered rule letting a retry reuse a truth-only floor (B2's floor builder's is truth-only; `track_b/README.md:133`) would save those days, but no such rule exists. Each retry re-scores its bite null against the rebuilt floor; earlier bite results are not reused, and they are recorded as exposure.

As scenarios, not expectations: if two of the three gates need a second attempt, rework adds **37–66 d** depending on which two (CE-G and SSI-G 37–51; CE-G and WP-G 43–61; WP-G and SSI-G 46–66), or 219–344 d with the base; if all three do, **63–89 d**, or **245–367 d** with the base.

**Lanes for tier 1.** Four lanes run at once after approval: a data-and-audit lane (D1, D4, D2, IR0, then D3), and one lane each for CE, WP and SSI. Each lane runs its rows serially. Elapsed times are engineer-day equivalents from the start, at 4 engineer-days a lane-week.

- Data-and-audit lane: D1 ends at 10–14, D4 at 14–21, D2 at 19–29, IR0 at **25–38 d**, and D3 at 28–42.
- WP lane: WP2 (4–6) runs while D1 does. WP1, WP3 and WP4 follow D1 and end at 30–44; WP5 ends at 39–57; WP6 ends at **42–62 d**.
- CE lane: CE0 ends at 2–4, D5 at 5–9, CE1 at 9–15 and CE2 at 15–24; CE3 ends at 20–31; CE4 waits for IR0 and ends at 31–47; CE5 ends at **33–50 d**.
- SSI lane: SSI0 and SSI1 end at 8–12; SSI2 waits for D4's state-supplement parameters and WP2 and ends at 20–30; SSI3 ends at 21–32; SSI4 waits for D2 and IR0 and ends at 33–50; SSI5 ends at 39–59; SSI5R ends at **41–62 d**.

So **all three tier-1 gates' first attempts are published after about 42–62 engineer-day equivalents, or 10.5–15.5 lane-weeks**, excluding queues and holidays. Started in early November 2026, that is mid-January to late February 2027, subject to d1899 (§2.7), §7.2's U2 sequencing rule for publication, and the Synthetic Beta's application and Gold Standard File validation times, which are external and excluded. IR0 gates CE4, WP5 and SSI4: CE4 and SSI4 wait for it at both ends of the range, and WP5 does not. None of tier 1 waits on B2's successor.

**Tier 2 waits on prerequisites outside this lane.** SSI6 can follow SSI5R and WP6 on the PSID cohorts the engine already projects (frame-relative), at 47–70 d. SSI9 needs Track B's I, which follows H, R2 and R3, with B0.2 for its timing gate (`parity-forecast-20261021.md:68`). SSI8, SSI6b, SSI7, WP8, C2 and C3 need a representative start, which waits on d947 and a certified frame. SSI7 also needs B4, the rules lane's insured-status rule and SSI9. C1's arm (a) needs only C0 and WP6's concept layer. C1's arm (b), C2 and C3 need J and their B7 scope prerequisites; in the coordinator's revision 2, B7 lands 5 March to 30 May 2027 with no second attempts, and 15 June to 22 October 2027 under its stress scenario, both counted from a B2-successor result on 20 November to 11 December (`:15–23, 58, 72`).

### 4.4 Against the coordinator's estimate

The coordinator did not allocate its rough estimates across readers, audit, implementation and comparisons, so whether its rows include the data and audit work this design prices separately is unconfirmed. Allocating shared costs before comparing rows:

| Group | Coordinator (order of magnitude) | This design |
|---|---|---|
| Covered earnings (CE0–CE5) | 8–12 d | 25–38 d |
| SSI (SSI0–SSI5R, SSI6, SSI6b, SSI7, SSI8, SSI9) | 10–20 d | 64–97 d |
| Wealth, pensions and other income (WP1–WP6, WP8) | 30–60 d | 39–59 d |
| **Three implementation groups** | **48–92 d** | **128–194 d** |
| Shared data, audit and comparisons (D1–D5, IR0, C0–C3) | not allocated | 54–84 d |
| **All** | **48–92 d** | **182–278 d** |

The wealth group lands inside the coordinator's range; covered earnings and SSI do not. The difference in covered earnings comes from the unread pre-2003 job context, the unadjudicated government codes and a gate whose bite must be shown (§3.1); in SSI from estimating take-up, building a complete input contract, a conformance gate, the timing and caseload gates the ledger's test requires, and SSI for blind and disabled adults. Comparing paired endpoints, this design's total is about 3.8 times the coordinator's at the low end (182 against 48) and 3.0 times at the high end (278 against 92); those ratios compare endpoints and are not an uncertainty bound.

## 5. Data sources and access per gate

Status as of 23 October 2026, checked against the lane's source catalog (`EV/income-resources-20261021/research/data-sources.md`, verified 22 October; "catalog §n" below). Facts the catalog marks unverified are marked so here. "Staged" means the files are on this machine and a reader exists or is named. SIPP, SCF and HRS microdata are not staged (`~/PolicyEngine/sipp-data` does not exist). Every PSID row is subject to d1899 (§2.7).

| Gate or use | Source | Role | Access | Lead time | Staged |
|---|---|---|---|---|---|
| CE-G | SSA 2006 EPUF, 1 percent sample, 1951–2006 | Gate truth (cohort, sex, age cells) | Public download | None | Yes (`epuf.py`) |
| CE-G | SSA Annual Statistical Supplement Table 4.B10, covered workers and taxable earnings by state (2025 edition the latest complete; catalog §11) | Gate truth if IR0 powers the state cell family | Public | None | No (D4) |
| CE-G | SIPP Synthetic Beta, version 7: covered and noncovered detailed-earnings-record earnings, 1978–2014; validation on the Gold Standard File by Census staff (catalog §5) | Gate truth if IR0 admits it | Application; Census expects decisions within five business days; validation as little as seven business days, with no guaranteed turnaround | External, excluded | No (D5) |
| CE-G | PSID family files 1968–2023 | Model input | PSID registration (Max's account), under the conditions in §2.7 | None | Yes |
| CE3, CE-G context | SSA Annual Statistical Supplement Tables 4.B1, 4.B2 and 4.B11; Census Annual Survey of Public Pensions (2025; catalog §22); SSA's Section 218 coverage references (catalog §23). No annual series of noncovered state and local employment was found | Classifier inputs; report-only context | Public | None | No (D4) |
| WP-G | PSID wealth: supplements 2005 and 2007; family-file composites 2009–2023 | Training and held-out waves (split at IR0) | PSID registration | None | Yes |
| WP-G | PSID 2025 early release: selected wealth and housing content for families interviewed in 2023 and 2025, un-imputed (catalog §1) | Candidate extra held-out wave | PSID registration | None | No |
| WP-G | PSID wealth supplements 1984, 1989, 1994, 1999, 2001, 2003. The 1984–1994 modules hold IRAs inside broader asset items, not as a separate balance (catalog §1) | Training history | PSID Data Center, login-gated | About a day | No (D1) |
| WP-G | PSID pension section and income items: 1984 coverage, plan type and balance (section C); 1999 onward plan type, balances and expected benefits (section P) and annuity and IRA additions and cash-outs (section W); 1989 and 1994 detail unverified (catalog §1) | Training and held-out | In the family files | None | Read for 2005–2013 only |
| WP-G | Careers for lifetime-earnings groups | Group definitions | Repository code (`lifetime_measures.py`) on PSID careers | None | Code exists |
| WP8 | SCF 2019, 2022 and 2025 (released 9 October 2026; catalog §6) | Report-only context | Public download | None | No (D3) |
| WP8 | Federal Reserve Financial Accounts (2026 Q2; codes renumbered June 2026); DOL Private Pension Plan Bulletin (2023 the latest verified); IRS SOI IRA tables (tax year 2023); BLS NCS (March 2026); CPS ASEC pension and retirement-distribution items (income year 2024 the latest verified) (catalog §§10, 18–21) | Report-only context | Public | None | No (D4) |
| SSI-C | 20 CFR part 416; POMS SI chapters, including SI 01415's annual state-supplement parameters for 1999–2026 (catalog §14); 42 U.S.C. 1381–1383f | Worked examples | Public | None | Partly (§2.5 captures) |
| SSI-C | policyengine.py and the PE-US release it certifies (PyPI); rulespec-us (GitHub) | Rules engine; differential | Public | None | PE-US 2.18.0 installed; 2.2.1 compared; 2.53.1 excerpts preserved |
| SSI4, SSI-G, SSI9 | SIPP 2018–2025 releases (reference years 2017–2024), monthly records; SSI items `RSSI_YRYN`, `RSSI_MNYN`, `TSSI_AMT` (catalog §4) | Take-up training; one release held out; timing gate | Public download, no registration | None | No (D2) |
| SSI4, SSI-G | PSID head and wife SSI items (2023: `G25F`, `G26F`, generated SSI income; a full historical concordance unverified; catalog §1) | Take-up training; held-out waves | In the family files | None | Read for 2005–2013 only |
| SSI8, SSI-G context | SSA SSI Annual Statistical Report (2025, Tables 4 and 5 by age and category; catalog §12); Annual Statistical Supplement Tables 7.A–7.E and 3.C6; SSI Recipients by State and County (2025; catalog §15) | SSI8's truth; report-only context for SSI-G | Public | None | No (D4) |
| SSI0 | Immigration status and qualifying quarters | Eligibility inputs | SIPP citizenship items; for the PSID and the frame, a source or a registered assumption chosen in SSI0 | None | Not yet sourced |
| Excluded | HRS and RAND HRS (2024 core early release); HRS–SSA restricted earnings, benefits and SSI records (SSI January 1974–December 2024); applications decided in about 6–8 weeks (catalog §§7–9) | Not used; would strengthen pension wealth and take-up | Registration; restricted access | Weeks to months | No; unpriced (§11) |

Two sources named in revision 2 are gone: SSA's *State Assistance Programs for SSI Recipients* ended with its January 2011 edition (catalog §13), replaced here by POMS SI 01415 and *SSI Recipients by State and County*; and no published series of noncovered state and local employees was found (catalog §23). Each source's own terms of use are checked in D1–D5 as well as its access route. Exposure on file for these sources is listed in §7.2.

## 6. Comparison targets

These are the DYNASIM and MINT tables this lane would be compared with. **The author opened no C1–C3 comparator cell.** Earlier published results the author encountered are disclosed in §13. Each target's titles come from a page the restricted list lets builders read, or from the repository's committed MINT8 guide; every cell is for a validation-only lane to transcribe and seal (C0).

- **DYNASIM3: Butrica and Uccello (2004), *How Will Boomers Fare at Retirement?*** Its list of tables (PDF pages 6–7, which the restricted list lets builders read) names, for individuals at age 67: household wealth (mean, median, by source; Tables 2–5), household income (mean, median, by source; Tables 8–11), replacement rates (Tables 13–14), the share below 200 percent of the poverty level and below 45 percent of the national average wage (Tables 22–23), and appendix tables of wealth and income by source, gender and marital status (appendix Tables 3–16 and 18). Exercise 2 used Tables 19 and 21, and U2 uses their 1946–55 column. Every results table of the report is restricted for builders (`RESTRICTED-FILES.md`, exercise 2). C1 needs the cohort columns whose 67th birthdays the PSID records; IR0 and C0 fix which.
- **MINT8 current-law profiles.** SSA publishes, for 2024, 2030, 2050 and 2070, profiles of beneficiaries aged 60 or older and of taxpayers aged 31 or older, with the household income distribution and mean shares by source (Social Security; annuitized asset income from DC plans and savings; DB pension income; all earnings, covered and noncovered; coresident income), household wealth including retirement accounts and excluding home equity, covered earnings, and poverty under the official and supplemental measures, overall and by race and ethnicity (MINT8 Table User Guide, committed capture `data/external/mint8_table_user_guide.source.html`, the sections "Interpreting the Profile of Beneficiaries" and "of Taxpayers"). Their 2024 cells can also be set beside observed 2024 survey data. The profile pages are not on the restricted list today; C0 adds them before any builder starts, as the A-COLA registration did for its sources.
- **Urban's published DYNASIM output.** The ledger cites Urban's DYNASIM output repositories, among them `dynasim-shiny2`, "Mean Income of People 62 and Older under Social Security Reform Options" (`docs/references.bib`, `urban2018dynasimshiny2`, dated 2018). Which DYNASIM version produced it is not established here; the comparator lane records it. The repositories are restricted for builders whole (`RESTRICTED-FILES.md`, NASI follow-ups). C3 would use their current-law rows only, through a validation-only lane.
- **Not comparison targets but validation sources:** EPUF; SSA's covered-worker, state, SSI and caseload tables; the SCF, SIPP and the Financial Accounts. They test the model; DYNASIM and MINT only sit beside it.

Any DYNASIM or MINT page that reports a reform's effect stays restricted under the existing entries, and C1–C3 use none of them. Since 21 October the restricted list also names three repository items that print DYNASIM results, `runs/m2_pseudo_projection_v1.json`, `benchmarks/wall.md` and the body of issue #113, for builders of by-group DYNASIM comparisons (`RESTRICTED-FILES.md`, 2026-10-21). C1–C3 report by group, so this lane's comparison builders open none of them, and the author has not.

## 7. Admission criteria and registration discipline

### 7.1 Rules

Track B §5.1 applies unchanged: each stage a new module and a new registered version; no edits to `engine/loop.py`, `engine/steps.py`, `gates.yaml`, committed `runs/*.json` or `src/populace_dynamics/track_b/`; everything frozen before any real-data outcome; exclusive output paths; published abort records. Track B §5.2's uncertainty rule applies to every empirical gate here: simultaneous 95 percent bounds over a registered cell family, survey-design resampling with family clusters, Monte Carlo error below a tenth of the tolerance, and insufficient precision reported as inconclusive, never as a pass.

Every gate and comparison is registered on issue #42 before it runs. Registrations are Max's; this lane drafts them and the coordinator brings them to him. Development and tests use invented data only. No real-PSID statistic is computed outside a registered step, and no small-cell PSID count goes to GitHub.

### 7.2 Exposure already on file

IR0 records these before proposing any holdout:

- **Exercise 2 (Registration 16)** used PSID income, SSI and WEALTH1 for the 2005–2013 waves, at age 67, with results public on #42; the parity ledger reports its headline (`docs/parity-ledger.md:131`), which this design's author read.
- **U2's step 4** computes, before registration, WEALTH1 quantiles, SSI receipt and recipient means by income year for the family units of the 1946–55 cohort around age 67, in waves through 2023 (`docs/design/boomers2004_1946_55_comparison.md:565–575`). Those waves overlap WP-G's and SSI-G's proposed holdouts. This design's author has not opened U2's step-4 outputs, and the builders of this lane's gates do not open them.
- **Registration 19** published static SSI and asset-test results on Microcosm's 2024 frame, and its §12 quotes a MINTEX projection of beneficiaries' marital status, which the author read.
- **`gate_epuf`** committed floors and bridges between PSID earnings and EPUF for 1998–2004 (`runs/epuf_gate_floors_v1.json`), so CE-G cells in those years are exposed.
- **`gate_epuf_fill`** used EPUF to certify career fills. Its reference arm scored all-covered PSID careers against EPUF's years-without-covered-earnings and low-earnings cells (`docs/parity-ledger.md:89`), so the all-covered proxy's performance on overlapping CE-G cells is already public; IR0 treats those cells as exposed.
- **The locked gates** in `gates.yaml` name no wealth, pension or SSI item (a search finds no match), and B2 gated earnings cells only.
- **This lane's own bite checks** (the all-covered proxy in CE4, M0 in WP5, the age-and-sex take-up null in SSI5 and SSI7, the carried-calibration null in SSI8) are recorded as exposure once scored.
- **The source catalog's own lane** opened two SSA aggregate-table pages while locating table titles and saw one search snippet with a projected pension outcome, which it omitted (catalog, governance status). None is a comparison target here; IR0 records them.

"Later" or "external" does not by itself make a holdout unused (Track B §5.2).

**U2 sequencing rule.** WP-G and SSI-G publish PSID wealth and SSI aggregates for the 2013 roster through 2023, which includes the 1946–55 cohort around age 67, and C1's arm (a) publishes PSID-realized income and wealth at 67. Those are the kind of real-PSID aggregates that bar a reader of U2's step-4 outputs from forecasting or checking U2 (`RESTRICTED-FILES.md`, 2026-10-21 entry on U2 step-4 run 2). So until U2's one-shot result is posted, no milestone here publishes, or posts to GitHub, any PSID statistic for the 1946–55 birth cohorts; if a gate must publish earlier, its outputs are first listed in `RESTRICTED-FILES.md` for U2's forecaster and checker, an entry the orchestrator makes.

### 7.3 Stage rules

- **Order in every gate.** IR0 freezes the cells, tolerance rule, pass conjunction and bite rule. The gate's block is drafted, refereed and registered on #42. Only after the registration pins its commit is the truth-only floor built; then the bite null is scored against it; only then is the candidate scored. No real-PSID statistic is computed before registration (§7.1).
- **CE-G.** If the all-covered proxy passes the cells CE v2 claims to fix, the gate stops (`WEAK_POWER_OR_VACUITY`) and is rescoped prospectively under a new registration. EPUF's disclosure operator (random rounding, band means near the cap; `epuf.py:20–28`) enters the floors. A Synthetic Beta cell counts only once the Gold Standard File validates it.
- **WP-G.** If M0 passes the cells its flaw predicts, the gate stops before M1 is scored. Otherwise M1 is scored and admitted only if it passes, whatever M0 does. A pass on exposed waves is retrospective regression evidence only.
- **SSI-C.** A refused configuration stays in every denominator. Agreement with PE-US or rulespec-us is diagnostic, not statutory acceptance (Track B §6, "Axiom coverage matrix").
- **SSI-G.** Take-up is fitted only on the training partition. SSA caseloads never tune it. Its bite null is a take-up model on age and sex only, scored after the floor and before SSI4's model; if the null passes the cells SSI4 claims to fix, the gate stops. Its admitted scope is annual-state receipt propensity, not actual receipt.
- **SSI8 and SSI9.** Registered on IR0's frozen records. IR0 freezes SSI8's rule (the minimum gap from the frame's calibration year, and the carried-calibration null); SSI8's record is completed for the certified frame's calibration year before SSI8 registers, and SSI8 shows the null failing before the model is scored. The frame's take-up flag and reported SSI are never read (§3.3).
- **C1–C3.** Track B §5.4's B7 requirements, and Track B §3.4's no-behavioral-response primary specification where the comparator assumes none.

## 8. Interfaces

### 8.1 Track B

This lane edits nothing under `src/populace_dynamics/track_b/`. It hands outputs to Track B through declared schemas and consumes Track B's outputs the same way.

- **H, the history recorder v2.** Track B's H keeps "labor, covered and RET-countable earnings kept separate" for 2010–2030 (Track B §3.1). CE5 supplies the source values of those channels for every PSID person-year from 1968, with status probabilities and the unresolved share, in a versioned table H reads. H owns recording; CE owns classification. Until CE5 passes, H's covered channel carries the legacy label "labor-income proxy".
- **B5, the earnings test in the projection.** The test counts noncovered wages and excludes pension payments (42 U.S.C. 403(f)(5)(C); §2.5). B5 therefore needs CE's RET-countable channel, not covered earnings, and WP's pension income never enters it. Without CE5, B5 must treat projected labor earnings as all covered and say so.
- **I, the monthly calendar.** I follows H, R2 and R3, with B0.2 for its observational timing gate (`parity-forecast-20261021.md:68`). SSI9 uses I's monthly mechanics and needs that timing gate wherever its estimands depend on event timing (Track B §3.4). Until SSI9 passes, this lane reports annualized potential SSI only.
- **J, joint validation.** J tests "joint earnings–claiming–DI states, payment and recipient denominators, and survivor pathways" on estimands frozen at B0.2 and ratified before B3 registers (Track B §3.4, §5.2). On current schedules SSI-G and SSI9 cannot pass before J's record is ratified (B3's window is 14 December to 17 January; `parity-forecast-20261021.md:65`), so J excludes SSI. C1's arm (b), C2 and C3 list SSI-inclusive cells in their B7 scope matrix as unsupported unless a separately registered joint Social Security–SSI gate passes.
- **B7.** Track B's scope matrix requires each target's "required non-Social-Security income" (§3.4). A B7 target that needs pensions, asset income or SSI is blocked until WP-G and SSI-G pass, until SSI9 for actual SSI receipt, until SSI7 for SSI under 65, and, for joint Social Security–SSI cells, until a joint gate passes (see J).
- **B4.** SSI7 needs B4's DI outcomes. WP's widowhood rule uses B4's endogenous widowhood once admitted; before that, WP-G runs on realized support.
- **B0.2.** IR0 reuses B0.2's protocol and record format (PR #554) if B0.2's is frozen. Whether IR0's records sit inside B0.2's or beside it is the coordinator's call.
- **Insured status.** SSI7 uses the rules lane's insured-status rule, which starts after #530 merges (`parity-forecast-20261021.md:49`).

### 8.2 PolicyEngine-US, policyengine.py and Axiom

- **PE-US computes SSI's rules**; this lane supplies inputs and projected parameters and never re-implements SSI's federal rules in Python. The existing static offset in `adjusted_poverty.py` stays as exercise 2's registered rule and becomes one differential case in SSI2.
- **SSI0 uses the latest policyengine.py interface.** Retaining direct PE-US internals requires a specific exception from Max, with its scope recorded (decision 6). Registration 19's ratified 2.18.0 run stays untouched.
- **The version conflict.** The latest policyengine.py certifies PE-US 2.2.1, which predates resource deeming (§2.4). Until a policyengine.py release certifies a PE-US with resource deeming, deeming configurations are refused and counted, or Max grants the exception.
- **Known gaps, refused or filed:** retirement funds as resources (§2.4); the spousal-deeming cap (Registration 19 §12, item 12); state supplements outside the encoded states. Each is filed on policyengine-us, and its rulespec-us mirror is handled as PolicyEngine's mirror rule requires (`~/PolicyEngine/CLAUDE.md:22–47`): encoded-correct with a cited test, encoded through the signed encoder, or queued as a dispatch-ready rulespec-us issue labelled `pe-parity` that carries the module path and corpus citation, the verbatim law, the required outputs, a pasteable `review_finding` and companion tests. A bare issue does not satisfy it.
- **Axiom.** Where rulespec-us encodes an SSI section (§2.4), SSI1 and SSI2 run differential checks against it. The coverage matrix is published with SSI2; agreement is diagnostic only.

### 8.3 Microcosm and the Microcosm-start plan

- The frame lacks DC balances, DB coverage and home value (`microcosm-start.md:282`). Its resource ownership is also unvalidated: microcosm#1215 places each household's liquid assets on one member and leaves everyone outside that member's marital unit at $0. **Unvalidated person and marital-unit resource ownership blocks SSI resource-test claims on a Microcosm start.** WP1 requests a corrected ownership contract and rebuilt, validated inputs, with evidence. PSID-start results are unaffected.
- WP3 is the Microcosm-start plan's rule and its check A1; T3, T10 and T12 overlap D1, WP1, WP3 and SSI6 (§4.3). Whichever plan builds a shared piece first owns it.

## 9. Invariants and tests per component

Each invariant below is stated in the PR that builds its component and tested with property-based tests (Hypothesis) beside example tests. Where two implementations of the same rule exist, a differential test checks they agree.

- **Coverage classifier (CE3).**
  - The four status probabilities are nonnegative and sum to one exactly.
  - Conservation: covered wages, covered self-employment, noncovered and unresolved earnings sum to the person-year's adjudicated labor income.
  - Statutory order: taxable wages are min(wages, cap); taxable self-employment is min(SE, max(0, cap − taxable wages)); no self-employment loss offsets wages; capped amounts never exceed the year's taxable maximum.
  - Nothing is covered while an applicable exclusion is unresolved.
  - Zero preservation: zero labor income gives zero in every channel.
  - Monotonicity: raising a component's noncoverage probability never raises its expected covered taxable amount.
  - RET-countable earnings equal covered wages plus noncovered wages plus net self-employment earnings, and never include pension payments.
  - Determinism under keyed draws; invariance to row order.
- **Wealth and pensions (WP1–WP6).**
  - Accounting identity: net worth equals assets less debts for every unit and wave; person allocations sum to the household's.
  - Balances are nonnegative; withdrawals never exceed balances; RMDs are met when they apply.
  - Events conserve: widowhood moves the household's assets to the survivor without creating any; a divorce split sums to the pre-divorce total; a death's assets leave as a recorded exit.
  - DB receipt, once started, is absorbing until death.
  - M0: equal input ranks give equal outputs. M1: donor transitions come only from wave pairs at or before the boundary; perturbing post-boundary data leaves fitted states and predictions unchanged (Track B §6's B2 test).
  - The annuity in WP6 reuses `annuity_factor_single` and `annuity_factor_joint`; a differential test checks WP6's income concept against exercise 2's on the same invented rows.
- **SSI (SSI0–SSI9).**
  - SSI is nonnegative and at most the applicable FBR plus any state supplement.
  - For a single recipient outside deeming, couple computation, caps and eligibility transitions, additional unearned income reduces positive federal SSI dollar for dollar, and additional earnings above the applicable exclusions reduce it by fifty cents. Couple totals and allocations, deeming caps and threshold crossings are tested separately.
  - Holding everything else fixed, SSI never rises when an individual's countable income or countable resources rise.
  - Under the frozen annual state, annualized potential SSI equals twelve times the monthly amount PE-US computes from equal twelfths.
  - The projected FBR is nondecreasing for a nonnegative COLA and is a multiple of $12 a year.
  - Registration 19's identity: SSI with the asset test equals SSI without it times the resource-test indicator (`pe_us_depletion_cut_population.md` §4.2).
  - Exercise 2's offset is the special case "existing recipients, no new eligibility": a differential test checks SSI2's computation against `_ssi_response` on invented rows.
  - A missing contract input refuses the case or applies its registered assumption; no PE-US default fills it silently.
  - Identical-policy baseline and reform runs match exactly.
- **Comparisons (C1–C3).** Definitions, denominators and cells are frozen before unsealing; no cell is selected or dropped afterwards; unsupported cells stay reported.

## 10. Risks and kill criteria

### 10.1 Blocking rule

Track B's rule applies unchanged (Track B §7): required-source unavailability, unresolved exposure, inadequate precision, unsupported critical configurations, or a failed gate or required regression test block the corresponding admission and its dependants. Fallbacks register before candidate outcomes. Failed or unsupported cells stay reported, and removing them cannot manufacture a pass.

### 10.2 Named conditions and what each stops

| Condition | Trigger | Stops |
|---|---|---|
| `COVERAGE_UNIDENTIFIED` | CE2 finds waves with no government or state information, so the unresolved share of a gated cell exceeds the limit IR0 freezes | CE-G for those cells; they stay report-only and `unresolved` |
| `EPUF_CONCEPT_MISMATCH` | EPUF's disclosure operator or its zero-row convention makes a cell's floor uninformative | That cell; if the gate's core cells, CE-G (prospective rescope) |
| `PSID_TERMS_UNRESOLVED` | d1899 unruled, or ruled so that agents may not use PSID data (§2.7) | Every row that reads PSID data; the lane returns with a redesign and a new price if agent use is ruled out |
| `WEAK_POWER_OR_VACUITY` | Power below 0.90, undefined cells, or a bite check that fails after the floor and before the candidate is scored: the all-covered proxy passes CE-G's target cells, M0 passes the cells its flaw predicts, SSI-G's or SSI7's age-and-sex null passes, or SSI8's carried-calibration null passes | That gate, pending a prospective rescope registered before candidate results |
| `WEALTH_WAVE_GAP` | Pre-1999 waves are five years apart, so donor transitions before 1999 cannot be two-year | M1 uses biennial transitions from 1999; earlier waves inform starting states only |
| `EXPOSURE_UNRESOLVED` | IR0 cannot establish an unused holdout (for example because of U2's step 4 or `gate_epuf`'s bridge) | The predictive label; a pass is regression evidence only |
| `SOURCE_UNAVAILABLE` | A wealth supplement, SIPP panel or state table cannot be obtained or verified | The gates that need it |
| `INPUT_CONTRACT_GAP` | SSI0 finds an input with no source and no defensible assumption (for example immigration status in the PSID) | The configurations that need it, refused and counted |
| `RULES_ENGINE_GAP` | PE-US, the release policyengine.py certifies, or rulespec-us cannot compute a configuration correctly | Those configurations, refused and counted; targets needing them blocked |
| `SSI_TIMING_UNADMITTED` | SSI9 fails, is inconclusive, or Track B's I and its timing gate are not admitted | Actual December receipt, annual payments, caseloads, SSI8, SSI7 and SSI6b |
| `TAKEUP_UNIDENTIFIED` | SSI-G fails or is inconclusive on take-up | Projected receipt; only full-take-up potential SSI is published, labelled as Registration 19's headline basis was |
| `DISABILITY_LINK_UNADMITTED` | No admitted disability determination without insured status | SSI under 65 (SSI7) |
| `FRAME_LACKS_RESOURCES` | Microcosm's frame lacks DC balances, DB coverage or home value, or its person and marital-unit resource ownership is unvalidated (microcosm#1215) | WP and SSI resource-test claims on a Microcosm start; PSID-start results continue |
| `RETURN_PATH_UNRULED` | No ruled return assumption for DC balances | M2 (WP7) |
| `REPRESENTATIVE_START_MISSING` | No representative starting population (d947 parked; frame not certified) | WP8, SSI8, SSI6b, SSI7, C2, C3 and national figures |
| `COMPARATOR_EXPOSED` | A builder of this lane opened a C1–C3 cell | That comparison's blind label |
| `GATE_FAIL_OR_REGRESSION_FAIL` | A registered gate here fails | Its admission and dependants; published with no seed selection or tolerance relief |
| `SUCCESSOR_EXHAUSTED` | Two independently justified successors of one mechanism fail | That mechanism, pending new evidence |

### 10.3 Kill criteria

1. **Covered earnings.** If the all-covered proxy, scored against CE4's floor, passes the cells CE v2 claims to fix in both EPUF's cells and the state cell family, CE4 stops before any CE v2 output is scored and CE v2 is published report-only. The ledger row then reads *Built, ungated*, and H's covered channel keeps its proxy label.
2. **Wealth and pensions.** If IR0 finds WP-G's core cells below 0.90 power using every held-out wave, WP-G is rescoped before candidates or becomes report-only, the path `gate_epuf` took. If M1 and one successor (M2 or an M1 revision) both fail, WP projection pauses, the row stays *None* for projection, and every B7 target that needs non-Social-Security income is blocked.
3. **SSI.** If take-up fails twice, the lane publishes only potential SSI at full take-up and stops projecting receipt. If SSI9 fails twice, caseload and payment claims stay blocked and SSI8 does not run.
4. **Track B.** If forward earnings reach `SUCCESSOR_EXHAUSTED`, tier 1 still stands, since none of it depends on B2, but C1's arm (b), C2, C3, SSI9, SSI8, SSI6b, SSI7 and SSI6's earnings inputs stop.
5. **PSID's terms.** If d1899 rules that agents may not use PSID data, every PSID row stops before it starts. The lane reports which gates survive on other sources whose terms allow agent use, and returns with a redesign and a new price for Max.

### 10.4 Attempt ledger

Each mechanism (coverage classification, wealth and pension transitions, SSI take-up, SSI timing) keeps a cumulative attempt ledger by gate family, as Track B does (Track B §7). Renaming a module or a registration does not reset it.

### 10.5 Risks most likely to slip

- **CE-G's bite.** `gate_epuf` failed its own bite check against EPUF (§2.1), noncoverage is diluted in EPUF's cells, and `gate_epuf_fill` already published the all-covered proxy's performance on overlapping cells (§7.2). The state cell family may rescue it, at the cost of small PSID state samples. IR0 judges its planning power, and CE4's proxy check decides, after the floor and before CE v2 is scored.
- **D1 and CE2.** Label verification across thirty to forty PSID waves is slow, and the covered-earnings campaign's sweep found 46 of 818 official prompts that broke a single-field rule (#403). Both are priced at their upper ends for that reason.
- **SSI0 and SSI4.** The input contract may find inputs the PSID never records, and simulating eligibility on SIPP is untested here; survey reports of SSI are known to be confused with Social Security.
- **WP5.** PSID wealth at older ages is thin, and the ledger's full cell list by cohort and lifetime-earnings group will not all reach power.
- **SSI2.** The rules lane's history (G v2's fifteen fix rounds; `parity-forecast-20261021.md:109`) says conformance work hardens slowly.
- **Tier 2.** Each row depends on prerequisites outside this lane.

## 11. Staffing and scope assumptions behind every estimate

- **Unit of effort.** One engineer-day is one day of reviewed output; one agent lane delivers about 4 engineer-days a week. Both are Track B's assumptions (Track B §8).
- **Four lanes** run tier 1 at once after approval: data and audit; covered earnings; wealth and pensions; SSI. Each runs its rows serially. Tier 2 runs on whichever lane is free once its prerequisites land.
- **All ranges are engineering judgments**, not demonstrated throughput, and mine unless they cite another document.
- **Excluded from the estimates:**
  - review and registration queues, including Max, the coordinator and referees;
  - HRS and SSA-linked restricted data, their access time and loaders;
  - Microcosm rebuilds, the frame's ownership fix and the other frame requests WP1 files;
  - PE-US, policyengine.py and rulespec-us fixes beyond filing them;
  - Track B's I and its timing gate, which SSI9 consumes;
  - the Synthetic Beta's application and the Gold Standard File's validation turnaround, which Census controls;
  - whatever d1899's answer requires;
  - second attempts, which §4.3 prices only as stress scenarios;
  - the conditional row WP7;
  - Subfleet lane availability.
- **Data.** PSID family files and EPUF are staged and assumed runnable. SIPP and SCF downloads are assumed to need no access time.

## 12. Decisions for Max

Each is a call this design cannot make. The coordinator brings them to Max; nothing below is decided.

0. **d1899, already queued (security): PSID's new prohibition on AI and LLM use with PSID data** (§2.7). It comes first because every PSID row here, and every PSID-based design in the project, depends on it.
1. **Retire the covered-earnings correction campaign and build CE v2?** Recommended. It keeps the old design's estimands and its fitting-free path, and drops the amendment ceremony. The alternative, restarting at Amendment 20, is not priced here.
2. **The return assumption for DC balances.** Needed only for M2 (WP7). The options are a deterministic path built on the selected baseline's interest rate, or a stochastic path. It is a methodology choice.
3. **Which population the income comparisons start from.** PSID cohorts now, or Microcosm's frame once d947 posts and the frame, including its resource ownership, is certified. SSI8, C2 and C3 need a representative start.
4. **SSI for blind and disabled adults in the first admission, or after B4 (SSI7)?** Recommended: after B4. SSI7 is in the base either way, because the ledger's test asks for participation by type.
5. **Register the comparison families on #42:** DYNASIM3's Boomers 2004 income and wealth tables (C1), MINT8's current-law profiles (C2) and Urban's published DYNASIM baseline output (C3). Each registration is Max's.
6. **An exception to PolicyEngine's interface rule?** The rule is to build on the latest policyengine.py. It certifies PE-US 2.2.1, a release older than the bridge's 2.18.0 and without resource deeming. Their federal SSI trees are the same (§2.4); the rest of 2.2.1's SSI chain is inventoried in SSI0. Recommended: no exception now; refuse and count deeming configurations until policyengine.py certifies a PE-US that has it, and come back if that has not happened by the time SSI2 registers.
7. **Start an HRS restricted-data application now?** Decisions take about 6–8 weeks and onboarding longer (catalog §9), and it is excluded from this design's estimates. It would strengthen pension wealth and take-up. Its terms would need the same check as PSID's.
8. **CE's projected-coverage sensitivity.** Proposed: treat all projected wages as covered, beside the primary rule of carrying the last observed status (§3.1).

## 13. Files and sources read, and exposure

**Read in this run** (master `1e739d32` unless noted): `docs/parity-ledger.md` in full; `docs/design/covered_earnings_correction.md` lines 1–346, 7099–7200, 8145–8200 and 9193–9240, plus its section headings; `docs/amendments/gate_epuf_registration_proposal.md` lines 1–40; `src/populace_dynamics/estimates/adjusted_poverty.py` lines 1–430, 840–920 and 1050–1633; `src/populace_dynamics/estimates/lifetime_measures.py` lines 1–45; `src/populace_dynamics/bridge/policyengine_us.py` lines 1–300 and 810–818; `docs/design/pe_us_depletion_cut_population.md` lines 1–120, §§2.3–2.4, 4 and 12; `docs/plans/microcosm-start.md` lines 1–60, 132–142, 253–330 and §4.2; `src/populace_dynamics/data/family_income.py` lines 1–120; `src/populace_dynamics/data/employer_dc.py` lines 1–110; `src/populace_dynamics/data/sipp_jobs.py` lines 1–70; `src/populace_dynamics/data/epuf.py` lines 1–60; `src/populace_dynamics/data/psid_job_context.py` lines 1–60 and `psid_job_context_registry.py` lines 270–320; `src/populace_dynamics/data/historical_coverage_rule_validation.py` lines 1–110; the docstrings of `covered_wage_history.py` and `psid_covered_earnings_registry.py`; `src/populace_dynamics/track_b/README.md`; `src/populace_dynamics/estimates/group_breakdown.py` lines 1–80; `docs/design/boomers2004_1946_55_comparison.md` lines 565–600; `gates.yaml` (a search for wealth, pension and SSI); `data/external/mint8_table_user_guide.source.html`, structure and the profile sections; issue #403; PR #405's summary; PR #386's summary; microcosm#1215; the Track B design, revision 3, §§1–8; the coordinator's forecast, revisions 1 and 2; the round-1, round-2 and round-3 reviews; the lane's source catalog (`research/data-sources.md`, sections 1–23 and its summary table); PSID's live Conditions of Use and two Internet Archive captures of it (§2.7), plus a presence check for the AI clause in nine earlier captures (November 2024 to July 2026); `RESTRICTED-FILES.md` in full, including its 2026-10-21 entries; PE-US 2.18.0's installed SSI variables and parameters named in §2.4; PE-US 2.2.1's federal SSI trees from its PyPI wheel, compared file by file with 2.18.0's (`sources/peus-2.2.1-vs-2.18.0-ssi.md`); PE-US 2.53.1's SSI resource files (preserved); PyPI metadata and upload dates for policyengine.py 6.10.0 and PE-US 2.2.1, 2.18.0 and 2.53.1; rulespec-us's file list at `5796861e5`; `~/PolicyEngine/CLAUDE.md` lines 1–100, the interface rule (lines 3–14) and the mirror rule (lines 22–47) among them; and the legal captures listed in `EV/income-resources-20261021/sources/MANIFEST.md`, including 42 U.S.C. 411(c) and 411(i).

**Exposure statement.** The author read `RESTRICTED-FILES.md` first and opened no file, page or line it lists, with one disclosure about how a permitted page was found. To find the readable list of tables in Butrica and Uccello (2004), a script extracted the text of PDF pages 1–9 and printed only per-page counts of three patterns; it then printed pages 6–7 (the list of tables and appendix tables, which builders may read) after a check, with digits masked, that those pages hold nothing else. No text of pages 1–5 or 8–9 reached the author. **The author opened no new C1–C3 comparator cell.** Two published results reached the author through permitted repository files: exercise 2's headline comparison with DYNASIM3's adjusted poverty change (`docs/parity-ledger.md:131`), and a MINTEX projection of beneficiaries' marital status quoted in Registration 19 (§12, item 6). IR0 records both. The author opened no comparator, seal, MINT profile or option page, no U2 step-4 output, none of `runs/m2_pseudo_projection_v1.json`, `benchmarks/wall.md` or issue #113's body, nothing of the Change.org/ASSEMBLY session, and no Track B outcome-aware file other than the parity ledger on master, which states B2's public result; the author is not a B2-successor builder and saw B0.2's PR #554 only by its title and its evidence folder only by its top-level listing. No PSID statistic was computed; PSID directories were listed by name only.

## 14. Review findings and where they are resolved

| Finding | Severity | Resolution |
|---|---|---|
| R1.1 SSI4 fits before IR0 freezes its partition | High | SSI4 depends on IR0, IR0 unlocks SSI4's partition (§4.1); schedule recomputed (§4.3) |
| R1.2 WP-G does not cover the whole wealth row | High | WP-G's cell families now follow the row's test, by cohort and lifetime-earnings group, partitioned by IR0's power audit; WP4, WP5 repriced; closure claims narrowed (§3.2, §4.1, §4.2) |
| R1.3 SSI5 credited with SSA-caseload validation | High | SSI5 narrowed to survey evidence; SSI8 added and priced (§3.3, §4.1, §4.2) |
| R1.4 C1(b) bypasses J and SSI6 | High | C1(b), C2 and C3 depend on SSI6, WP-G, SSI-G, B3L, B4, J and B7 scope prerequisites; C1(a) exempt (§1, §3.5, §4.1) |
| R1.5 Annual reporting does not remove SSI timing | High | Initial estimands are annualized potential benefits under a frozen annual state; SSI9 timing gate added and priced; SSI-G's payment estimand report-only (§3.3, §4.1, §8.1) |
| R1.6 SSI input contract incomplete | Medium | SSI0 publishes a complete source-to-input contract with refusals and assumptions; repriced 6–9 d (§3.3, §4.1, §5) |
| R1.7 POMS retirement-fund branch omitted | Medium | Full POMS treatment in §2.4; account access and periodic-payment states in D1, WP1, M1 and SSI0; SSI-C cases (§3.2, §3.3, §4.1) |
| R1.8 Legal mechanisms unread; private-worker fallback | Medium | Coverage and retirement statutes read and cited (§2.5); unread rules listed as research questions; covered only after every exclusion is resolved (§3.1, §9) |
| R1.9 Rework omits repeat gate work | Medium | Itemized retry costs with justified reuse (§4.3); labelled a stress assumption per the coordinator's correction |
| R1.10 Comparison with the coordinator assumes a scope split | Medium | §4.4 rewritten: allocation unconfirmed; implementation and shared costs separated; ratios described as paired endpoints |
| R1.11 Frame resource-ownership defect understated | Medium | §2.2, §8.3 and `FRAME_LACKS_RESOURCES` corrected; WP1 requests an ownership contract; exclusion listed in §11 |
| R1.12 Coverage sensitivity needs a job process | Medium | Replaced with an executable sensitivity; choice is decision 8 (§3.1, §12) |
| R1.13 SSI marginal-benefit property false | Medium | Replaced with the single-recipient form; couples and caps tested separately (§9) |
| R1.14 Interface mandate weakened | Medium | SSI0 uses the latest policyengine.py; exception is decision 6, with the version conflict stated (§2.4, §3.3, §8.2, §12) |
| R1.15 Exposure statement overstates blindness | Medium | Ledger and Registration 19 exposures disclosed; "no new C1–C3 comparator cell" (§6, §7.2, §13) |
| R1.16 References and dates | Low | Forecast citations moved to revision 2's lines and windows, with their qualification; read inventory reconciled (§2.6, §4.3, §13) |
| R1.17 State-supplement file inventory wrong | Low | Six states by file name (§2.4) |
| R1.18 Verification class missing for some milestones | Low | Every milestone has a row (§4.2) |
| Self-review 1–7 (`self-review-r0.md`) | — | State supplements (§2.4); M1 donor transitions (§3.2); IR0's dependency (§4.1); C3's DYNASIM version (§6, §12); gate record (§7.2); `gate_epuf`'s bridge (§7.2); CE-G's bite and the state cell family (§3.1, §7.3, §10.5) |
| Coordinator, 22 October: the rework rate is a stress assumption | — | §2.6 and §4.3 (completed in round 2, N1) |

**Round 2** (`review-r2.md`): the review found sixteen round-1 findings and six self-review items resolved, R1.18 and the coordinator's correction partly resolved, and twelve new findings.

| Finding | Severity | Resolution |
|---|---|---|
| R1.18 (partial) WP7 had no verification row | Low | WP7 row added to §4.2 |
| Coordinator correction (partial) / N1 rework used as a probability | Medium | §4.3 prices second attempts only as scenarios (two gates, all three), with no rate |
| N2 SSI-G's run and publication unpriced | Medium | SSI5R added (2–3 d); totals, schedule and retry table recomputed (§4.1, §4.3, §4.4) |
| N3 the bite check was circular and called truth-only | Medium | IR0 freezes the bite rule; CE4 scores the proxy after the floor and before CE v2; WP5 scores M0 before M1; bite results recorded as exposure, never reused (§3.1, §3.2, §4.1, §7.2, §7.3, §10) |
| N4 ministers' coverage misstated | Medium | §410(a)(8) with §411(c) and §411(i) stated correctly; the list marked not exhaustive (§2.5) |
| N5 the certified PE-US 2.2.1 was not inspected | Medium | 2.2.1's federal SSI trees compared file by file with 2.18.0's; SSI0 inventories the rest; decision 6 updated (§2.4, §12) |
| N6 SSI8 could pass on the frame's calibration | Medium | SSI4's take-up replaces the frame's flag; the carried-calibration null must fail first (§3.3, §4.1, §7.3, §10.2) |
| N7 SSI closure outside the base | Medium | SSI7 moved into tier 2; SSI6b added; SSI6 credits no ledger part (§4.1, §4.2, §4.3) |
| N8 publications could expose U2's forecaster | Medium | U2 sequencing rule (§7.2), referenced from §4.1 and §4.3 |
| N9 J's SSI branch could not occur | Low | J excludes SSI; joint cells unsupported unless a joint gate passes (§8.1) |
| N10 `gate_epuf_fill` already scored the all-covered proxy | Low | Recorded as exposure (§7.2, §10.5) |
| N11 the 72(t) tax treated as SSI's penalty | Low | Stated as an open question SSI2 settles (§3.2) |
| N12.1 D3 and IR0 | Low | D3 dropped from IR0's dependencies and scheduled after it (§4.1, §4.3) |
| N12.2 WP7 row | Low | Added (§4.2) |
| N12.3 §10.3(4) | Low | SSI8 and SSI6b added |
| N12.4 I's prerequisites | Low | "I follows H, R2 and R3, with B0.2 for its timing gate" (§4.3, §8.1) |
| N12.5 the mirror rule's dispatch-ready requirement | Low | Stated, with the read range (§8.2, §13) |
| N12.6 floor reuse without a registered rule | Low | Each retry rebuilds its floor; reuse would need a registered rule (§4.3) |

**Round 3** (`review-r3.md`): the review found every round-2 item resolved except N3 and N7, each partly resolved with a new finding.

| Finding | Severity | Resolution |
|---|---|---|
| F1 floors and bite checks computed before registration | Medium | Every gate registers first; the floor and bite null follow the registration's pinned commit, as B2's did (§3.1, §3.2, §3.3, §4.1, §4.3 retry table, §7.3) |
| F2 SSI7 and SSI6b cannot close their ledger parts | Medium | SSI7 depends on SSI9 and a representative start and extends SSI4's take-up (13–19 d); SSI6b gains blind and disabled cells after SSI7 and the poverty effect (3–5 d); the closure sentence and named conditions corrected (§3.3, §4.1, §4.2, §10.2) |
| F3 §10.3(4) omits SSI7 | Low | Added |
| F4 SSI-G's bite null undefined; retries skip the bite | Low | Age-and-sex take-up null defined for SSI-G and SSI7; each retry re-scores its null (1 d) (§3.3, §4.3, §7.2, §7.3, §10.2) |
| F5 the U2 list omits pre-run PSID outputs | Low | CE4, WP5 and SSI5 added (§4.1) |
| F6 IR0 cannot freeze SSI8's year | Low | IR0 freezes the rule; SSI8's record is completed for the certified frame before SSI8 registers (§3.3, §7.3) |

**The source catalog** (`research/data-sources.md`):

| Finding | Resolution |
|---|---|
| PSID's conditions of use prohibit AI and LLM use with PSID data | Verified on the live page and dated from archive captures; queued as d1899; every PSID row blocked (§2.7, §4.1, §4.3, §10.2, §10.3, §12) |
| SSA's *State Assistance Programs for SSI Recipients* ended in January 2011 | Replaced by POMS SI 01415 and *SSI Recipients by State and County* (§4.1 D4, §5) |
| No published series of noncovered state and local employment | CE3's priors re-sourced, with `unresolved` as the fallback (§3.1, §5) |
| The SIPP Synthetic Beta measures noncovered earnings directly | D5 added (3–5 d) and a third CE-G cell family (§3.1, §4.1, §5) |
| State covered workers are SSA Table 4.B10 | Named as the state cell family's source (§3.1, §5) |
| SIPP releases run 2018–2025 (reference years 2017–2024); the SCF 2025 is out; PSID has a 2025 early release | D2, D3 and WP-G updated (§3.2, §4.1, §5) |
| Pre-1999 PSID wealth modules hold IRAs inside broader items; pension detail varies by wave | Stated in §5 for D1 to handle |
