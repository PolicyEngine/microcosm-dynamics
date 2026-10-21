# Open population design, revision 3: births, migration, alignment and the long horizon

**Status:** design for approval, 21 October 2026. Nothing in it is built or registered. Max authorized this lane on 21 October 2026 (decision d1802); the coordinator walks him through approval, and no code is written before he approves. Every registration it names goes to issue #42 only through the coordinator, on Max's go.

**Every effort figure in this document is an estimate.** The figures are engineering judgments under the staffing assumptions in §9, not demonstrated throughput. "d" means engineer-days and "lw" means agent-lane weeks at 4 engineer-days per week; in every effort cell, lw = d ÷ 4 exactly.

**Pinned tree.** Repository citations are to `origin/master` at `1e739d32` (21 October 2026), read in this run. Package paths are under `src/populace_dynamics/` unless stated. Track B citations are to *Track B design, revision 3* (28 September 2026, approved by ruling d515), kept outside the repository at `~/microcosm-launch-evidence/dynasim-parity-20260909/trackb-design-20260928.md`.

**Revision log.**
- *Revision 1* (commit `d0082afc`) was the first submitted. Its independent review was queued and cancelled before it started, so no review finding has been resolved yet.
- *Revision 2* answers the coordinator's interface note of 21 October 2026: Track B's B0.2 audit (draft PR #554) will cite this design's price for entrant initialization and records only what B3 to J need from entrants. Entrant initialization is now one milestone row, OP8, with its estimate, data sources and deliverables to Track B (§3.1, §3.5, §4). Revision 1's OP8 (immigrants' economic state) and OP9 (newborns' economic entry) are merged into it, with a new sub-part for starting states in Track B's schemas, and the later rows are renumbered (OP10 → OP9, OP11a/b → OP10a/b, OP12a/b → OP11a/b, OP13 → OP12). Because B0.2 is already under way, §3.4 now measures the economic phase from a B2 successor's pass with B0.2 frozen, and gives the other case. §6.4 adds the two RESTRICTED-FILES entries of 21 October 2026. Its independent review was queued and cancelled before it started.
- *Revision 3* answers the coordinator's correction of 21 October 2026: the insured-status rule has an owner. Under d1802, Track B's rules lane builds it as a separate PR once #530 merges (quarters of coverage; fully, currently and disability insured, including the special rules before 31 and for blindness; the date last insured; designed for B6a's person-month risk set; its estimate 5–10 d). OP8(d) now consumes that rule through an interface written down in §6.1, which says how the pre-entry covered-work convention enters the quarters-of-coverage count. Revision 2's decision 7 (who owns the rule) and its 4–7 d scale figure are gone; later decisions are renumbered.

## In brief

This lane owns four rows of the parity ledger (`docs/parity-ledger.md`): births, immigration and emigration, alignment and a representative population, and projections beyond 2030. The only price on record for any of it is design B's B8 (2032/2050 horizons plus population extension, income and wealth gates included): 40–70 d, an estimate made before the M6 assembly's limits for people who enter later (§2.4) were written down.

The design splits the work in two:

- **A demographic phase that can start now.** Newborns with both parent links, immigrant cohorts sized to the Trustees' gross inflow, an emigration law, an alignment layer that keeps the unaligned path as the scored object, a 2013→2020 retrodiction of the population's composition, and the demographic projection to 2100. None of it needs forward earnings, so none of it waits on Track B. Ten items (OP0.1, OP1 to OP7, OP10a, OP11a), **71–105 d** of effort (estimate), about 43–63 engineer-day equivalents elapsed on two lanes.
- **An economic phase that waits on Track B.** Entrant initialization (OP8: entrants' starting states, earnings state, covered-work histories and insured status, and newborns' earnings entry at 16–24 with the hand-off to Track B's law at 25); alignment to labor targets; the economic long horizon; matched 2050, 2065 and 2070 comparisons; and a gate on aligned SSA benefit and payment totals. Six items (OP0.2, OP8, OP9, OP10b, OP11b, OP12), **62–100 d** (estimate). They depend on Track B's H, B3, B4 and J, so none but OP0.2 can start until a successor to B2 passes (ruling d1659); the last lands about 68–109 engineer-day equivalents after that day if Track B's B0.2 (draft PR #554) has frozen by then, and if Track B keeps its own estimates.

**All 15 milestone rows (OP0 counts once): 133–205 d, or 33.25–51.25 lw (estimate).** **Entrant initialization, which Track B §3.3 left unpriced, is its own row, OP8: 25–39 d, or 6.25–9.75 lw (estimate).** It builds on demographic packets that OP2 and OP3 already pay for (9–13 d), so its full price is 34–52 d (§3.5). Insured status itself comes from Track B's insured-status rule, which OP8 consumes through the interface in §6.1 and does not price.

Three findings shape the design:

1. The certified M6 assembly simulates marriage, fertility, disability and household composition once per draw over panels built before the first projected year, and its panel builders refuse any horizon but 2022 (§2.4). Nobody who enters after the first year can marry, give birth, become disabled or join a household through it. Open-population processes therefore run through forward-mode adapters, which Track B's B4 owns for incumbents.
2. Scheduled entrants make a projection's early years depend on its end year: on invented data, runs to 2035 and to 2045 differ from 2026 on, while the same runs without entrants are identical (§2.9). Production runs therefore use one registered horizon and read shorter horizons as prefixes.
3. Two earlier designs, for immigration (#218) and alignment (#217), closed unmerged on 25 September 2026. This design keeps their core rulings, prices them and adds what they left out: newborns' links and states, an emigration law, a population-composition gate and the horizon (§2.8).

## 1. Purpose

Each ledger row states the test that would show parity. This design plans the milestones that would meet each test, with a gate or an explicit report-only label at every step.

| Ledger row | The row's test (from `docs/parity-ledger.md`) |
|---|---|
| Births | Projected births against vital statistics; newborns' links to both parents, households and starting states; their entry into later earnings, disability and benefit processes |
| Immigration and emigration | Arrivals and departures sized to OACT's assumptions; entrants' covered-work histories and insured status; their benefit receipt against SSA statistics |
| Alignment and a representative population | An alignment step to the actuaries' demographic and labor targets that keeps households consistent, with its displacement from the unaligned path published; gated SSA benefit and payment totals |
| Projections beyond 2030 | Near-term gates first (gate 3); then matched 2050, 2065 and 2070 comparisons and 75-year sensitivity surfaces on named assumption paths, each registered before it runs |

Track B's rules carry over unchanged (Track B §1, §5.1): each mechanism, population and horizon is admitted separately, through a registered gate against independent observations; no DYNASIM comparison may select structure, parameters, denominators or rows; DYNASIM agreement never rescues a failed gate.

One rule specific to this lane comes from M6's decision 9, which the closed alignment design quotes ("Alignment layer report-only; gate the un-aligned drift", PR #217 §1.2): **the unaligned projection is the scientific object that gates score; the aligned projection is a labeled production companion whose displacement is published.**

## 2. What exists now

I read every source cited in this section in this run, at `1e739d32`.

### 2.1 The loop and its seams

- **Eight adapters in a fixed order.** `engine/loop.py:117–129` defines `PeriodModules`: mortality, aging, marital core, fertility, disability, earnings, claiming and household composition, plus an optional initializer. The loop calls them in that order each year (`loop.py:297–350`).
- **No emigration or alignment step.** None of the eight adapters removes a living person or reconciles to an external target.
- **One entry seam.** Scheduled entrants arrive through `metadata["m6_scheduled_entries_by_year"]` (`loop.py:27`). The loop validates each frame (`:226–240`), rejects IDs that appear twice (`:242–250`), and appends the year's entrants before that year's mortality draw (`:271–286`).
- **Identifiers and random streams.** A projection-wide `SyntheticPersonIdAllocator` hands out new IDs and refuses reserved real ones (`loop.py:43–64`; created at `:251–262` unless the caller supplies one). Each person's stream is keyed by an ordinal: initial and scheduled IDs get ordinals in sorted order before the first year (`:263–266`); anyone else, such as a newborn, gets the next ordinal at the end of the year they appear (`:358–360`). The stream for a period and module does not depend on the projection's length: `rng.py:61–67` takes the `period`-th child of a fresh root sequence.
- **Sealed files.** `engine/loop.py` and `engine/steps.py` sit inside the source identity that the first-estimates birth-evidence reducer seals: every file under the package outside `POST_REVIEW_SOURCE_EXCLUSIONS` must equal reviewed commit `1c7f3540` (`ss/statutory_aime.py:137–141`; the exclusion tuple starts at `scripts/first_estimates_birth_evidence.py:135`, and `entrant_schedule.py` and `entrant_domains.py` are on it at `:176–178`). Track B §5.1 also forbids edits to `engine/loop.py`, `engine/steps.py`, `gates.yaml` and committed `runs/*.json`. Every new module this lane adds must join the exclusion tuple, which `tests/estimates/test_birth_evidence_artifact.py:68` pins exactly, with a transitive reachability test like `tests/track_u2/test_u2_isolation.py:242`.

### 2.2 Births

- **The closed projections draw none.** The registered Track A and FRA-68 projections are closed cohorts whose fertility slot draws no births (`baselines/fertility.py:8–11`).
- **Gate m6's engine materializes them, report-only.** Its reference draw added 316 newborns (`runs/gate_m6_candidate3_v1.json`, `family_b.entrants.family_b_open_additions.synthetic_births`), and the gate names entrants, births and open-panel margins as report-only (`gates.yaml:5416–5420`).
- **What a newborn gets.** `steps.materialize_maternal_births` (`steps.py:451–507`) gives each child a new ID from the projection's allocator, age 0, its birth year, a sex drawn 50/50 from the fertility module's stream (`:494–496`), a link to the mother (`:497`), and the mother's `household_id`, `weight` and `start_weight` (`:499–503`). Every other roster column is missing, because the child rows are built on the roster's columns and only these are filled (`:485–487`). There is no second-parent link; the paternal "shadow" births are household conditioning draws and are deliberately not materialized (`:459–461`).
- **Timing.** Births are appended in step 4, after step 1's deaths, so no newborn can die in its birth year; its first mortality draw comes the next year at age 0 (`loop.py:297–323`; `steps.py:113–134`).
- **The gated fertility kernel.** Candidate 16's maternal-birth kernel draws each woman-year from her age, parity and birth decade (`engine/marital.py:376–382`), with parity starting at zero when the simulation starts (`:363`). In the M6 assembly it runs once per draw over the cached marital panel (§2.4).
- **The opt-in ASFR step.** `baselines/fertility.py` draws one Bernoulli birth per exposed woman-year at a baseline's single-age rate, at most one birth a year (`:14–22`), from a person-keyed tagged stream (`:24–28`), and materializes children through the same function (`:181`). It is labeled "not gated, report-only" (`:59`), and no registered test uses it (`:8–12`).

### 2.3 Scheduled entrants

- **A report-only cohort builder.** `engine/entrant_schedule.py` turns a donor frame and annual controls in thousands into seam-ready frames (`:185–396`). It sizes cohorts to the Trustees' gross positive inflow (LPR inflow plus temporary-or-unlawfully-present inflow) and excludes outflow, adjustment of status and total net change (`:37–42`, `:359–364`). It reweights donors rather than resampling them, so it consumes no random draws (`:44–48`). Its provenance says `gated: False`, `report_only: True` (`:387–388`).
- **Its timing convention is the seam's.** An entrant for year Y carries `year = Y − 1` and `age = entry_age`, faces a mortality draw at the entry age, then ages (`:14–22`; `docs/entrant-seam.md`, "Existing loop timing").
- **What it lacks.** The readers for controls and donors were not carried over (`entrant_schedule.py:41–42`; `docs/entrant-seam.md:1–7`), so no committed run has added an immigrant; gate m6 records `immigrant_cohorts: 0`, a value its runner writes as a constant (`harness/m6_runner.py:1027`, `:1212`).
- **Entrants are kept out of every fitted domain.** `engine/entrant_domains.py:49–74` lists four exclusions and why: fertility risk (no parity seed), claiming (no insured-status test), the disability panel (entrants are not PSID panel members) and the earnings domain (no fitted 2014 state). Benefit outputs for entrants are blanked to missing, never zero (`:210–228`); a claiming wrapper runs the claiming step on incumbents only (`:312–380`); and the exclusion report says `execution_verified: False` (`:244–262`).
- **ID reuse is checked outside the loop.** `validate_projection_allocator` refuses metadata whose allocator could reuse a known ID (`entrant_schedule.py:457–507`). The loop does not check it, because changing `loop.py` needs a re-pin of the reducer seal (`:472–476`).

### 2.4 What the M6 assembly can and cannot carry for people who enter later

`engine/assembly.py:234–447` wires the certified fitted objects into the eight slots:

- **Marital core:** built once per draw from the period-1 frame through the panel builder, simulated for the whole window, and cached (`:282–299`).
- **Fertility:** drawn for the cached marital IDs only (`:319–329`).
- **Disability:** a reproduction over realized PSID support rows for the window, simulated once (`:340–379`).
- **Household composition:** built and simulated once (`:403–422`).
- **Earnings:** the forward law behind the earnings-domain wrapper (`:243`, `:390–391`); people without the fitted 2014 state get the pinned non-scored zero (`engine/earnings_domain.py:1–7`).
- **Claiming:** `apply_claiming`, which draws a claim age for everyone 50 or older with no insured-status test (`steps.py:390–448`, `:411–413`).

The three cached updates join the live roster by a left merge on `person_id` (`_merge_period_columns`, `assembly.py:174–192`), so a person absent from a nonempty update gets missing marital, disability and household values. The panel builders refuse any horizon but 2022 (`engine/panel_builders.py:27`, `:128–131`).

**Consequence.** The certified assembly cannot carry anyone who enters after its first year through marriage, fertility, disability or household processes, and cannot run past 2022. Open-population processes need forward-mode, live-roster adapters. Track B's B4 owns that successor for incumbents: forward support, redrawn initial states, and M6's marriage and divorce composed with death-triggered widowhood (Track B §3.1). B4 also declares closed-population versus entrant coverage (Track B §3.4). The forward support contract already exists and refuses realized holdout inputs (`engine/support.py:236–252`).

### 2.5 Emigration and alignment

- **Emigration.** The US engine has none (§2.1); `entrant_schedule.py:361` records "the engine has no emigration law". The experimental accountant has an `EMIGRATION` event kind (`engine/accounting.py:87–95`) but generates no events (`:1–8`). The UK engine has a net-migration step that adds or removes people by an age-indexed net rate (`uk/household_transitions.py:779–851`); nothing in the US engine uses it.
- **Alignment.** The engine has no alignment step. Gate m6 records its alignment displacement as `not_computed` with reason `alignment_layer_output_not_collected` (`runs/gate_m6_candidate3_v1.json`, `family_b.alignment_displacement`; the runner calls `build_alignment_displacement(None, None)` at `harness/m6_runner.py:1249`). That function already computes per-year displacement between an unaligned and an aligned frame and refuses unequal keys, so a missing row cannot pass as zero displacement (`harness/m6_reporting.py:321–415`).

### 2.6 Horizon

- The loop accepts any end year (`loop.py:170–201`).
- The 2026 Trustees baseline runs to 2100 (`baselines/tr2026_intermediate.py:75`) and CBO's to 2099 (`baselines/cbo2026_long_term.py:1–36`). Both are for invented-data projections only: `build_track_a_inputs` refuses a real-data run under them (`baselines/__init__.py:21–29`; `baselines/track_a.py:18–41`).
- Gate m6 certifies its 2015–2022 temporal holdout only; the 2100 extrapolation is "a decision-5 successor gate, not certified here" (`gates.yaml:5426–5430`). Gate 3 is unlocked and has no cells (`gates.yaml:2898–2905`).

### 2.7 Inputs already pinned, and what is missing

- **Trustees Report 2026.** The repository transcribes Tables V.C1, V.B1, VI.G1, V.A1 and V.A4 and OACT's period death probabilities (`data/tr2026.py:3–4`). Its single-age fertility is a fixed shape scaled each year to V.A1's TFR, because the public single-year tables publish no age schedule (`baselines/tr2026_intermediate.py:21–27`). It transcribes neither the immigration table nor the population table.
- **The immigration and population tables.** I fetched both on 21 October 2026 and read only their titles and column headers. Table V.A2, *Immigration Assumptions, Calendar Years 1940–2100* (in thousands), gives LPR and temporary-or-unlawfully-present inflow, outflow, adjustments of status and net change, and total net change, for history and the intermediate, low-cost and high-cost alternatives. Table V.A3, *Social Security Area Population on July 1 and Dependency Ratios, Calendar Years 1941–2100*, gives population in three age groups (under 20, 20–64, 65 and over) and dependency ratios. Neither is single-age.
- **Access.** On 21 October 2026 SSA's site returned a 404-byte body to a request with a browser user agent and HTTP 403 to a fetch tool, and served both pages to the `Wget/1.21.4` user agent that the TR2026 capture lane used (`data/external/tr2026/provenance.md:10–17`). That file records that HTML hashes change between live fetches, so captures pin the captured bytes.
- **CBO 2026.** The repository pins CBO's single-age fertility for all, native-born and foreign-born women, 2021–2099; death rates by age and sex; and covered workers by sex and covered earnings, 2026–2100 (`data/external/cbo2026/provenance.md:29–56`). CBO's January 2026 demographic workbook is pinned by hash with only TFR and life-expectancy rows transcribed (same file, `:36–38`).

### 2.8 Two closed designs and one open issue

- **Immigration, PR #218** (docs only, closed unmerged 25 September 2026). Its rulings, which this design keeps: entrants are built before the projection and enter only through the existing seam; the size control is the Trustees' positive inflow, never total net change, and emigration is a separate exit law; donors supply state only through entry, never a cloned future; a proposed `gate_imm` fits on the 2010–2013 annual ACS 1-year PUMS files and scores the separately weighted 2014 file on recent arrivals' characteristics, floors first; and the Social Security area is not the resident population, so a named universe bridge is required. Its §4.8 lists the entry-state packet each downstream module needs.
- **Alignment, PR #217** (docs only, closed unmerged 25 September 2026). Its rulings, kept: certification runs are unaligned; the aligned run is a separate replay with fresh state that never overwrites the unaligned one; discrete events are reconciled by deterministic whole-unit selection with fixed person weights; covered wages, a continuous value, by one disclosed scalar; displacement goes through `build_alignment_displacement` with per-margin, per-year attribution; and a target that a summary table cannot supply (V.A1's TFR is not an age schedule) stays `not_available` rather than invented.
- **Issue #412** (open) records what Microcosm's node graph means for dynamics: per-year alignment would become a REWEIGHT node, and immigrant entry needs an interface amendment because Microcosm's EXPAND requires every new row to name a source. It names #218's seam as the consumer of that amendment.

Both closed designs cite file and line numbers in older trees. I re-verified at `1e739d32` every mechanism this design takes from them.

### 2.9 A finding: with scheduled entrants, early years depend on the end year

`docs/design/open_population_evidence/horizon_dependence.py` runs the existing loop on an invented 400-person roster to 2035 and to 2045, once with births only and once with immigrant cohorts scheduled for every year through the end year. Its committed output (`horizon_dependence.txt`) shows the closed runs' slices identical in every shared year, 2026–2035, and the open runs' slices different in every shared year, with row counts diverging from 2027.

The mechanism follows from §2.1: every scheduled entrant through the end year gets an ordinal before the first year, so a later end year moves every newborn's ordinal, and with it the newborn's random stream; the allocator's starting ID moves too. Without entrants, ordinals do not depend on the end year.

**Consequence for this design.** A production projection uses one registered horizon (the baseline's last year, 2100 for TR2026) and reads shorter horizons as prefixes of that run. OP1 enforces this, and §7 makes it a property test. Gate runs have their own fixed horizons and are never compared across horizons.

### 2.10 Constraints on every milestone

- No edits to the sealed files of §2.1, to `gates.yaml` or to committed runs; new modules join the reducer's exclusion tuple with reachability tests.
- No edits to `src/populace_dynamics/track_b/`. This lane consumes Track B's outputs through declared interfaces (§6.1).
- Builds and tests use invented data. Real-data steps are registered steps; no real PSID statistic is computed outside one, and no small-cell PSID count goes to GitHub.
- `~/microcosm-launch-evidence/dynasim-parity-20260909/RESTRICTED-FILES.md` governs every lane. The entries that bind this lane are in §6.4.

## 3. Staged milestones

### 3.1 Milestone table

Milestones OP0.1 to OP7, OP10a and OP11a form the demographic phase; OP0.2, OP8, OP9, OP10b, OP11b and OP12 form the economic phase. Gate names are proposals; each registers on #42 through the coordinator.

| Id | Deliverable | Verification or gate | Effort estimate (d / lw) | Depends on | Unlocks |
|---|---|---|---|---|---|
| **OP0** | Source, exposure, access and power audit for every open-population gate and target manifest. OP0.1 covers the demographic phase: `gate_birth`, `gate_imm`, the emigration check, the demographic target manifest, `gate_pop` and the demographic horizon record. OP0.2 covers the economic phase: `gate_entrant_earn`, `gate_young_earn`, the labor target manifest, the long-horizon backtest, OP11b's comparators and `gate_ssa_totals` | One frozen record per gate with the ten elements of §5.2 and a named power procedure; a blinded review of feasibility and power before any of those gates registers | 8–12 / 2–3 (OP0.1: 5–7 / 1.25–1.75; OP0.2: 3–5 / 0.75–1.25) | Track B's frozen audit protocol (Track B §5.2), reused; OP0.2 also Track B's B0.2 record (draft PR #554) | Registration of every OP gate |
| **OP1** | Open-population harness around the sealed loop: an exit adapter in the mortality slot (deaths drawn exactly as now; emigration drawn among survivors from its own tagged stream); a birth-entry adapter in the fertility slot; the scheduled-entry seam with the projection's own allocator and `validate_projection_allocator`; one registered horizon per production run (§2.9); per-year `reconcile_period` and run-level `reconcile_history` with declared birth, entry, death and emigration events; an unaligned-only facade for gate runs; reducer-seal exclusions and reachability tests | Accounting conformance: count identities exact and weight identities within the reported summation residual every year; with emigration switched off, survivors equal the closed run's exactly; the §7 properties on invented data | 6–9 / 1.5–2.25 | None (invented data) | OP2, OP3, OP4, OP6 |
| **OP2** | Births v2. (a) The newborn entry packet: mother link; second-parent link (the mother's spouse or partner in the authoritative marital state in the birth year, otherwise an explicit unlinked reason); sex from a person-keyed stream at a pinned NCHS sex ratio; household, weight and birth order; out-of-domain markers for adult processes; the fields Track B's G reads for child benefits. (b) Live-roster fertility: candidate 16's kernel run year by year on the live roster, with parity seeds from a registered imputation (candidates: own children in the household, or the CPS June Fertility Supplement's children ever born) and a declared rule for birth decades outside its fit. (c) `gate_birth` | (a), (b): conformance, including a differential test that the live-roster kernel reproduces the cached kernel on a closed panel. (c) `gate_birth`: births by mother's five-year age group and the share male, against NCHS natality for held-out years 2015–2019, on the unaligned path from OP5's start with OP3's and OP4's flows, floors first. The share of births to married mothers is report-only until B4 draws marriages in the projection | 10–16 / 2.5–4 ((a) 4–6, (b) 3–5, (c) 3–5) | OP0.1, OP1; (c) also OP3, OP4 and OP5; second-parent links for marriages formed after the start need B4's forward marital state | OP6, OP7, OP8 |
| **OP3** | Immigrant entry. A reader for V.A2's components, 1940–2100, with a registered bridge from the Social Security area to the resident roster; an ACS 1-year PUMS reader for 2010–2014 with replicate weights and per-year concept maps; the immigrant demographic packet (age, sex, nativity, reported entry year, arrival unit and its links, marital state, a parity seed for women by the same registered imputation as OP2(b), disability proxy) under #218's rules; schedules through `build_entrant_schedule`; `gate_imm` | `gate_imm`: recent-arrival characteristics and named joints, fitted on ACS 2010–2013 and scored once on the separately weighted 2014 file, floors first (#218 §5). Admits a stock proxy, not arrival-time truth | 14–20 / 3.5–5 (controls and bridge 3–4; ACS reader 3–4; packet 5–7; gate 3–5) | OP0.1, OP1 | OP2(c), OP5, OP6, OP7, OP8 |
| **OP4** | Emigration. An exit law by age, sex, nativity and years since entry, with family or individual exit per a registered rule, sized to V.A2's outflow columns; relational updates (a spouse who emigrates leaves the marriage as "abroad", never as a death); emigrants' exits recorded so that OP12 can count those insured | Accounting conformance and alignment to the outflow controls. Composition is report-only unless OP0.1 finds an admissible holdout; the candidate check is the decline of ACS arrival cohorts between 2015 and 2019 net of mortality | 8–12 / 2–3 (law and controls 3–4; relational updates 2–3; exit records 1–2; check 2–3) | OP0.1, OP1 | OP2(c), OP6, OP7 |
| **OP5** | A national demographic start for the retrodiction gates: everyone in the ACS 2013 1-year PUMS with households, spouse and parent links inside the household, nativity and reported entry year, weighted. ACS 2013 keeps `gate_imm`'s 2014 holdout unread | Conformance: the start reproduces its own weighted ACS tabulations exactly; reported against Census's 2013 population estimates | 4–6 / 1–1.5 | OP0.1, OP3's ACS reader | OP2(c), OP7 |
| **OP6** | Demographic alignment: the aligned production replay with fresh state; whole-unit selection for deaths by age and sex, births by mother's age, and emigration by category, each against the target manifest; immigration aligned by construction; households kept consistent (an aligned death triggers widowhood exactly as a drawn death does); displacement per margin and year through `build_alignment_displacement`; displacement corridors set before release | Production integrity, not a scientific gate: the aligned margin is within the selection-resolution floor plus a pinned numeric tolerance (#217 §6.2); the unaligned artifact is byte-identical whether the aligned producer is importable or not | 8–12 / 2–3 | OP2(a)(b), OP3, OP4 | OP9, OP10a, OP12 |
| **OP7** | `gate_pop`: project OP5's 2013 start to 2020 on the unaligned path with births, deaths, immigration and emigration, and score population by sex and five-year age group, and the foreign-born by period of entry | `gate_pop`: against the 2020 Census by age and sex and the ACS 2019 1-year file for the foreign-born, floors first. Its arms (fitted laws with 2013-vintage assumptions, or realized aggregate controls) are frozen at OP0.1 | 6–8 / 1.5–2 | OP2, OP3, OP4, OP5 | OP10a |
| **OP8** | **Entrant initialization**, the item Track B §3.3 left unpriced, for immigrants and newborns, delivered to Track B as one atomic bundle per entrant (§3.5 lists what goes to each Track B milestone). (a) Starting states in Track B's schemas: marital state and duration, spouse and household links, parity seed, a disability state at entry by a registered mapping or an explicit out-of-domain marker, and the year the entrant joins each risk set. (b) Immigrants' earnings anchors and latent state: earnings and employment at entry from the donor packet, and the forward law's state (`u_w` and its lags) mapped into the law's rank space by a declared rule. (c) Covered-work histories: pre-entry US covered years under the convention Max picks (§10, decision 4), never silently zero; post-entry accrual through H; quarters of coverage by year. (d) Insured status: computed from (c) by Track B's insured-status rule through the §6.1 interface, as a determined status or "undetermined" where unavailable pre-entry years could change it, with `entrant_domains.py`'s claiming and DI exclusions lifted only where it is computable. (e) Newborns' economic entry: participation and earnings at 16–24 (the same module serves incumbents under 25) and the hand-off state at 25 in Track B's rank space. (f) Two gates | (a), (c), (d): conformance and the §7 properties. (f) `gate_entrant_earn`: earnings and employment of the 2010–2014 arrival cohorts in the ACS 2019 1-year file, by years since arrival, age and sex, projected from their entry bundles through Track B's admitted law. `gate_young_earn`: early-career covered earnings in SSA's 2006 EPUF on a new salt disjoint from `gate_epuf_fill`'s and H1's test sets, and CPS ASEC earnings at 18–24 in held-out years. Passing both lifts Track B's `ENTRANT_INIT_UNADMITTED` for the states they cover | 25–39 / 6.25–9.75 ((a) 3–5; (b) 5–8; (c) 2–4; (d) 2–3; (e) 6–9; (f) 7–10, of which `gate_entrant_earn` 3–4 and `gate_young_earn` 4–6) | OP0.2; OP2 and OP3 (the demographic packets); Track B's H and B3 for (c) and (e), and B4 for (a), (b) and `gate_entrant_earn`; Track B's agreement to the hand-off interface for (e); Track B's insured-status rule (rules lane, a separate PR after #530) for (d) | OP9, OP10b, OP12; Track B's B4 open coverage, B5, B6a, J and B7 targets that need open coverage |
| **OP9** | Labor alignment on the aligned replay: covered workers selected to Table IV.B4's concept (workers with covered earnings at any time in the year), average covered wage by one scalar to V.B1's growth, with chain-state updates coherent with Track B's law | Production integrity, as OP6; displacement and corridors published | 8–12 / 2–3 | OP0.2, OP6, Track B's B4 | OP12 |
| **OP10a** | The demographic horizon to 2100: declared rules for every demographic component outside its fitted support (fertility birth decades, marital decades, migration controls); a Leslie-matrix differential test; demographic sensitivity surfaces on the TR2026 intermediate, low-cost and high-cost paths and CBO's | Mechanics and sensitivity only. The horizon record (§5.2) labels every year past 2030 "conditional on named assumptions" | 6–9 / 1.5–2.25 | OP6, OP7 | OP11a |
| **OP10b** | The economic horizon and its license record: declared rules for every economic component past its fitted support (the earnings law's wage normalization to the baseline AWI, DI rates, the claim table); an open-population sibling of Track B's B3L backtest; economic sensitivity surfaces | Retrospective regression evidence and sensitivity. The license record admits a year past 2030 only as a conditional projection, never a validated one | 8–12 / 2–3 | OP8, OP9, Track B's J | OP11b |
| **OP11a** | Registered, report-only comparisons of the projected population in 2050, 2065 and 2070 by age group and nativity with OACT (V.A3), CBO and the Census Bureau's 2023 projections | Registered cross-model comparison; agreement or disagreement only | 4–6 / 1–1.5 | OP10a | None |
| **OP11b** | Registered comparisons in 2050, 2065 and 2070 of beneficiaries, benefits and the income measures DYNASIM and MINT publish, with OACT and CBO first and DYNASIM one of several (d660); DYNASIM comparisons follow Track B's B7 blind protocol | Registered comparison with a sealed comparator where DYNASIM or MINT is involved; not a validation gate | 10–20 / 2.5–5, only after target-specific prerequisites pass | OP10b, Track B's J | None |
| **OP12** | `gate_ssa_totals`: aligned SSA beneficiary counts and benefit and payment totals by type, on the aligned open population started from Microcosm | Held-out years of SSA's Annual Statistical Supplement chosen at OP0.2 after its exposure record (§4) | 8–12 / 2–3 | OP0.2, OP6, OP8, OP9, Track B's J, I and G (v2 and part 2), the Microcosm start's gate 3, an insured-status rule | Track B's B7 targets that need open coverage; M7 |

### 3.2 Verification class and admitted scope per milestone

The classes are Track B's (Track B §3.2), with "production integrity" added for alignment, which admits nothing scientific.

| Id | Verification class | Admitted scope on success |
|---|---|---|
| OP0 | Source audit | Nothing scientific. It authorizes registration of the named gates on their frozen records |
| OP1 | Accounting conformance | Stock-flow identities and seam mechanics only |
| OP2 (a), (b) | Accounting conformance; differential conformance for the live-roster kernel | The newborn packet's structure, and equality with the cached kernel on closed panels. No new fertility claim |
| OP2 (c) | Held-out prediction where OP0.1 certifies 2015–2019 natality unused; otherwise retrospective regression | Births by mother's age group and the share male, for OP5's population with OP3's and OP4's flows, in the registered years |
| OP3 | Held-out prediction on the ACS 2014 recent-arrival stock proxy | Entrants' demographic composition as a stock proxy, conditional on the control. Not gross flows, arrival-time state, legal status or anything after entry |
| OP4 | Accounting conformance; alignment to controls | Exit totals by category. Composition stays report-only unless the check becomes a gate at OP0.1 |
| OP5 | Accounting conformance | A weighted start that reproduces its source |
| OP6, OP9 | Production integrity | That the disclosed reconciler produced the pinned scenario. Nothing about the transition laws it corrects |
| OP7 | Held-out prediction (retrodiction) | The unaligned demographic machinery's 2013→2020 composition by age, sex and nativity for OP5's population |
| OP8 (a), (c), (d) | Accounting and statutory conformance | Entrants' starting states, covered-work histories and insured status as constructed objects that obey the §7 properties. No population claim |
| OP8 (b), (e), (f) | Held-out prediction | Through `gate_entrant_earn`: immigrants' entry earnings state and its five-to-nine-year evolution under Track B's law, for the registered cohorts. Through `gate_young_earn`: earnings at 16–24 and the hand-off at 25, for the registered cohorts. Each lifts `ENTRANT_INIT_UNADMITTED` for the states it covers only |
| OP10a, OP10b | Mechanics, retrospective regression and sensitivity | A year past 2030 as a conditional projection under named assumptions, with drift diagnostics. Never a validated forecast; `HORIZON_NOT_LICENSED` (Track B §7) stays in force for any claim framed as validated |
| OP11a, OP11b | Registered cross-model comparison | Agreement or disagreement on the frozen targets only |
| OP12 | Held-out prediction | Aligned beneficiary counts and totals for the registered types and years |

**Downstream consequence**, as in Track B §3.2: if `gate_pop`, `gate_entrant_earn` or `gate_young_earn` passes only on exposed data, later admissions cannot cite it as independent predictive evidence.

### 3.3 Ledger rows each milestone closes

| Ledger row | Part of the row's test | Closed by | Status after those milestones |
|---|---|---|---|
| Births | Projected births against vital statistics | OP2(c) | *Gate passed* for births, if `gate_birth` passes |
| | Newborns' links to both parents, households and starting states | OP2(a); B4 for marriages formed after the start | Built and conformance-tested once OP2 lands, for mothers whose partnership exists in the projection's marital state; complete once B4 draws marriages in the projection |
| | Their entry into later earnings, disability and benefit processes | OP8(e) and `gate_young_earn` for earnings; B4 and J for disability and family processes; Track B's insured-status rule | Complete only when `gate_young_earn` and J pass |
| Immigration and emigration | Arrivals and departures sized to OACT's assumptions | OP3, OP4, OP6 | Arrivals: *Gate passed* for composition, aligned for totals. Departures: aligned for totals, report-only for composition |
| | Entrants' covered-work histories and insured status | OP8(c) and (d), with H and Track B's insured-status rule; `gate_entrant_earn` | Built and conformance-tested once OP8 lands; *Gate passed* for immigrants' earnings state once `gate_entrant_earn` passes |
| | Their benefit receipt against SSA statistics | OP12 | *Gate passed* once OP12 passes |
| Alignment and a representative population | Alignment to demographic and labor targets that keeps households consistent, with displacement published | OP6, OP9 | *Report-only* by design: alignment is production integrity, with published displacement |
| | Gated SSA benefit and payment totals | OP12 | *Gate passed* once OP12 passes |
| | A representative population | The Microcosm start (`docs/plans/microcosm-start.md`, d947), not this lane | Unchanged by this lane |
| Projections beyond 2030 | Near-term gates first (gate 3) | The Microcosm start's gate 3, not this lane | Unchanged by this lane |
| | Matched 2050, 2065 and 2070 comparisons | OP11a, OP11b | *Report-only*: registered comparisons |
| | 75-year sensitivity surfaces on named assumption paths, each registered | OP10a, OP10b | *Report-only*, conditional projections |

### 3.4 Totals and critical path (all estimates)

**Totals.** All rows: **133–205 d, or 33.25–51.25 lw**. The demographic phase (OP0.1, OP1 to OP7, OP10a, OP11a) is 71–105 d (17.75–26.25 lw); the economic phase (OP0.2, OP8, OP9, OP10b, OP11b, OP12) is 62–100 d (15.5–25 lw).

The arithmetic, from the §3.1 cells:
- Demographic: OP0.1 (5–7) + OP1 (6–9) + OP2 (10–16) + OP3 (14–20) + OP4 (8–12) + OP5 (4–6) + OP6 (8–12) + OP7 (6–8) + OP10a (6–9) + OP11a (4–6) = 71–105.
- Economic: OP0.2 (3–5) + OP8 (25–39) + OP9 (8–12) + OP10b (8–12) + OP11b (10–20) + OP12 (8–12) = 62–100.
- OP8's sub-parts: (a) 3–5 + (b) 5–8 + (c) 2–4 + (d) 2–3 + (e) 6–9 + (f) 7–10 = 25–39.

**Demographic phase on two lanes (D1, D2), from approval.**
- OP0.1 on D1 and OP1 on D2 run together and both finish after 6–9 d.
- D1: OP3, finishing after 20–29 d; then OP5, 24–35; then OP6, which needs OP2(a)(b), OP3 and OP4 and so starts when OP5 frees D1, finishing after 32–47.
- D2: OP2(a)(b), finishing after 13–20; OP4, 21–32; then OP2(c), which needs OP5, starting at 24–35 and finishing after 27–40; then OP7, finishing after 33–48.
- OP10a starts when OP6 and OP7 are both done (33–48) and finishes after 39–57; OP11a finishes after **43–63 engineer-day equivalents**.

**Economic phase, measured from T, the day a B2 successor passes its registered gate.** T itself is unknown: ruling d1659 requires the successor's design to come to Max first. Track B's B0.2 is already under way (draft PR #554), so this schedule assumes its record is frozen by T. Track B's chain after T, from its §3.1 cells and ignoring queues, is then: H (done at T+6–9), B3 (T+14–21), B3L (T+19–29), B4 (T+31–47), B5 (T+36–55), B6a (T+42–65) and J (T+50–77).
- OP0.2 follows Track B's B0.2 record, so it can finish before T and is off the path.
- E1: OP8(c), covered-work histories, follows H: T+6–9 to T+8–13. OP8(e) and `gate_young_earn` follow B3: T+14–21 to T+24–36.
- E2: OP8(a), starting states in B4's schemas, runs once B4 starts (after B3L): T+19–29 to T+22–34, so B4 can declare open coverage.
- E1: OP8(b), (d) and `gate_entrant_earn` follow B4: T+31–47 to T+41–62. OP8 is then complete.
- E2: OP9 follows B4 and OP6: T+31–47 to T+39–59.
- OP10b (E2) and OP12 (E1) follow J, OP8 and OP9: both run T+50–77 to T+58–89.
- OP11b follows OP10b: T+58–89 to **T+68–109**.

If B0.2 instead freezes after T, as Track B §3.3's sequence had it, add B0.2's 5–7 d to every T-relative figure above: the last milestone lands at T+73–116. Either way, the economic phase's elapsed time is set by Track B's chain to J, not by this lane's effort.

### 3.5 Entrant initialization: the price Track B §3.3 left open

Track B §3.4 says entrants "require admitted initialization of earnings anchors, latent state, covered histories, insured status and demographic state", and §3.3 lists entrant initialization as unpriced. **This design prices it as one milestone row, OP8: 25–39 d, or 6.25–9.75 lw (estimate).** Track B's B0.2 audit (draft PR #554) can cite that row; it records what B3 to J need from entrants and does not price this work itself.

**What OP8 delivers to Track B.** One atomic bundle per entrant (the shape #218 §4.8 calls an `EntrantStateBundle`), keyed by person ID, with `entry_kind` (`maternal_birth` or `immigrant_cohort`) and entry year, built from invented data until each real-data step is registered:

| Track B milestone | What it receives from OP8 | OP8 sub-part |
|---|---|---|
| H (history recorder) | A history opened at entry: pre-entry US covered years under the registered convention, kept distinct from zero; quarters of coverage by year; exits by death and by emigration kept apart | (c) |
| B3 and its successor law | For immigrants, the law's state at entry (`u_w` and its lags) in the law's rank space; for newborns, the hand-off state at 25 | (b), (e) |
| B4 (forward projection) | Starting states in B4's schemas: marital state and duration, spouse and household links, parity seed, disability state or out-of-domain marker, and the year each entrant joins each risk set; with OP3's entrant weights by kind and year for B4's coverage declaration | (a) |
| B5, B6a and I | Insured status by the admitted rule, and eligibility-domain flags that keep an entrant out of claiming and DI until insured status is computable | (d) |
| J and B7 | Whether `ENTRANT_INIT_UNADMITTED` is lifted, and for which states, from `gate_entrant_earn` and `gate_young_earn`; entrant weights by kind and year for coverage declarations | (f) |

**Data sources for OP8** (detail and exposure in §4):
- ACS 1-year PUMS: 2010–2014 (OP3's donors) for entry earnings, employment, marital and household state and disability items; 2019 for `gate_entrant_earn`.
- SSA's 2006 EPUF (in the repository, pinned by #509) and CPS ASEC for earnings at 16–24 and `gate_young_earn`.
- The CPS June Fertility Supplement for parity seeds, if OP0.1 picks it (OP2(b)).
- SSA's quarter-of-coverage amounts by year and the crediting rules Track M already implements, for (c); Track B's insured-status rule, through the §6.1 interface, for (d).
- Track B's law and H, through their declared interfaces only.

**The full price of entrant initialization** adds the demographic packets OP8 builds on, which the demographic phase already pays for because its own gates need them:

| Component | Where | Estimate |
|---|---|---|
| Newborns' demographic packet: parent links, sex, household, weight, birth order, out-of-domain markers | OP2(a) | 4–6 d |
| Immigrants' demographic packet: age, sex, nativity, reported entry year, arrival unit and links, marital state, parity seed, disability proxy | OP3 (packet) | 5–7 d |
| Entrant initialization proper | OP8 | 25–39 d |
| **Total** | | **34–52 d (estimate)** |
| Insured-status rule: quarters of coverage; fully, currently and disability insured, including the special rules before 31 and for blindness; the date last insured | Track B's rules lane under d1802, a separate PR once #530 merges; OP8(d) consumes it through the §6.1 interface | Track B's estimate, 5–10 d (as the coordinator relayed it on 21 October 2026); outside every total here |

**Is it on Track B's path to B7?** Only if B7's frozen target needs open coverage. A target defined on people alive at the start and aged 62 or older at a 2030 horizon contains no newborns; post-start immigrants enter it only if they arrive in their late fifties or older, and OP3's schedule reports their weight, so B7 can declare closed coverage under Track B §3.4 and state what it excludes. National totals, payroll and any horizon past the mid-2030s need open coverage.

### 3.6 Still unpriced

These must be priced before a complete budget is approved:
- an "abroad" ledger that keeps insured emigrants' benefits in national totals (OP4 records exits and OP12 counts insured emigrants; paying them is a separate deliverable);
- totalization agreements, under which some immigrants count foreign coverage toward insured status;
- a covered-earnings bridge for temporary or unlawfully present entrants, whose covered share the ACS does not observe;
- a successor to the M4 disability model for anyone outside its PSID panel (Track B's B4 limits DI outcomes; a forward disability hazard for entrants is not in any priced row);
- moving the engine into Microcosm as an operator (#412), which the Microcosm start also leaves out;
- data-access time for any source OP0 finds restricted (OACT single-age fertility or population, if they must be requested);
- review and registration queues.

## 4. Data sources and access per gate

| Gate or record | Sources | Access | Exposure on record | Holdout |
|---|---|---|---|---|
| `gate_birth` (OP2) | NCHS natality (NVSS birth data, CDC WONDER): births by mother's age, child's sex, mother's marital status, birth order; Census population estimates for denominators; for parity seeds, the CPS June Fertility Supplement (children ever born) | Public downloads | NCHS 2023 and 2024 age-specific rates are in the repository: gate 2's external anchor (`scripts/fetch_nchs_asfr.py`, `scripts/build_gate2_floors.py`) and the TR2026 baseline's default shape (`data/external/nchs_asfr_2024.json`). A text search for "natality" finds only that fetch script | 2015–2019; 2020–2022 diagnostic, as in gate m6's shock window (`gates.yaml:5411–5415`) |
| `gate_imm` (OP3) | ACS 1-year PUMS 2010–2014 (person, household, replicate weights); TR2026 V.A2; the Trustees' glossary and the 2026 long-range model documentation (pinned in `docs/baselines.md`) for the universe bridge | Public Census downloads; SSA pages need the `Wget` user agent (§2.7) | A text search finds ACS tables named as anchors in the gate 2b and 2c floor builders and in U2's source registry; OP0.1 establishes whether any ACS PUMS year was read | 2014 annual file (#218 §5.2) |
| Emigration check (OP4) | V.A2 outflow columns; the Census Bureau's 2023 national projections methodology, for its emigration assumptions (to be confirmed at OP0.1); ACS arrival cohorts across 2015–2019 | Public | None known | Report-only unless OP0.1 admits a holdout |
| Demographic target manifest (OP6) | V.A1 (TFR), V.A2, OACT's death probabilities (pinned), CBO's single-age fertility by nativity (pinned); V.A3 and V.A4 as validation only | Public; pinned files in `data/external/` | V.A1 and V.A4 transcribed (`data/tr2026.py`) | Not a gate |
| OP5 start, `gate_pop` (OP7) | ACS 2013 1-year PUMS (start); 2020 Census by single age and sex; ACS 2019 1-year (foreign-born by period of entry); Census population estimates (report-only) | Public | None known | 2020 Census; ACS 2019 |
| OP8 (a)–(d), entrant initialization (not gates) | ACS 1-year PUMS 2010–2014 donor items (earnings, employment, disability items, marital status and relationships); the CPS June Fertility Supplement for parity seeds if OP0.1 picks it; SSA's quarter-of-coverage amounts by year and the crediting rules Track M already implements for years of coverage (`min_benefit_track_m/coverage.py:1–30`); Social Security Act §§214 and 223(c) for insured status | Public; Track M's code in the repository | ACS 2010–2014 also fit OP3 | Not a gate: conformance and the §7 properties |
| `gate_entrant_earn` (OP8) | ACS 2019 1-year PUMS for the 2010–2014 arrival cohorts; the immigrant earnings work in *Social Security Bulletin* 68(1), 2008, by Duleep and Dowhan, as cited by #218 §2.1, as a report-only benchmark | Public | ACS 2010–2014 used to fit OP3 | ACS 2019 |
| `gate_young_earn` (OP8) | SSA's 2006 EPUF (pinned by #509); CPS ASEC earnings at 18–24 | EPUF in the repository; CPS public | EPUF is heavily exposed: `gate_epuf`, `gate_epuf_fill` and the Microcosm start's H1 SSA arm use it with their own salts; OP0.2 must draw a new, disjoint salt and disclose the overlap | EPUF persons on the new salt; CPS years frozen at OP0.2 |
| Labor target manifest (OP9) | TR2026 IV.B4 (covered workers) and V.B1 (average covered wage growth); CBO's covered workers by sex, 2026–2100 (pinned) | Public | IV.B4 is named in RESTRICTED-FILES for A-COLA builders (§6.4) | Not a gate |
| Long-horizon backtest (OP10b) | PSID 2006→2022, as Track B's B3L; ACS 2005→2022 for composition | PSID local; ACS public | PSID fully exposed (B3L's label applies: regression evidence) | None independent |
| OP11a, OP11b comparisons | V.A3; CBO's January 2026 demographic projections (pinned zip); Census 2023 national projections; OACT and CBO beneficiary projections; MINT8 and DYNASIM output tables | Public; DYNASIM and MINT tables only through a validation-only comparator lane | DYNASIM output and MINT option tables are restricted (§6.4) | Sealed comparators |
| `gate_ssa_totals` (OP12) | SSA Annual Statistical Supplement beneficiaries and benefits by type | Public | Track B participants opened the 2023, 2024 and 2025 supplements' §4.B, §6.B and §6.E (Track B §5.2); the Microcosm start's W2 reads the 2023 edition's 5.B1, 5.D1 and 5.G1 | Years and tables chosen at OP0.2 after that record; exposed ones are regression evidence |

## 5. Admission criteria and registration discipline

### 5.1 General rules

These apply to every OP milestone, in addition to Track B §5.1:
- Each milestone adds new modules and a new registered version; it edits no sealed file, no `track_b/` file, no `gates.yaml` cell and no committed run.
- Gate runs go through an unaligned-only facade whose request cannot carry a target bundle; the aligned producer is outside the gate runner's import closure (#217 §4.1).
- Sources, module versions, seeds, populations, estimands, tolerances and alternatives are frozen before any real-data outcome is computed. Output paths are exclusive, and abort records are published.
- Every production run uses one registered horizon (§2.9).
- Every milestone reports its verification class and admitted scope (§3.2).

### 5.2 What OP0 freezes

OP0 produces one frozen record per gate, with Track B §5.2's ten elements: source release, variables, population, exposure history, holdout partition, critical cells, numerical tolerances, uncertainty treatment, pass conjunction and the named power procedure. It adds three elements this lane needs:
- **the universe** of each source and its bridge to the projection's roster (Social Security area, resident population, civilian noninstitutional population);
- **the target manifest**: for each external target, its table, row, column, vintage, captured-byte hash and status (`available`, `not_available` or `validation_only`), as #217 §7.1 specifies;
- **the horizon record**: for each fitted component, its fitted support and the declared rule outside it.

OP0.1 must also establish whether OACT publishes single-age fertility and single-age population projections; the public single-year tables do not (§2.7). Where it does not, the margin uses a registered bridge (the TR2026 baseline's derived shape, or CBO's single-age rates) or stays `not_available`.

### 5.3 Proposed numerical limits

**Proposals only, subject to OP0's prospective feasibility and power review**, which may rescope before any candidate result and may never loosen a limit after one.

- **Gated cells** use the repository's floor-pricing convention: the statistic |ln(candidate / reference)|; tolerance round(mean + 4·sd, 3) of a real-versus-real floor built from household-disjoint half-splits (ACS: replicate weights per year); a cell is gate-eligible only with at least 20 events on the weaker half and a stabilized tolerance at most T_max = ln(1.5) (`gates.yaml:1336`, `:1001–1006`). Cells that fail eligibility are report-only by the floor's own machine partition.
- **Uncertainty**, as Track B §5.2: simultaneous 95 percent bounds with Bonferroni over each registered cell family; resampling that respects survey design and households; Monte Carlo error below one-tenth of each tolerance; insufficient precision is inconclusive, never a pass.
- **Alignment fidelity** (OP6, OP9): the aligned margin within its selection-resolution floor plus a numeric tolerance pinned in target units (#217 §6.1–6.2). Displacement corridors are authored before release; until a corridor artifact exists, each run publishes raw displacement with `corridor_status: not_available`.
- **Horizon drift** (OP10b): none proposed. OP0.2 freezes limits on drift growth for the backtest.

### 5.4 Stage-specific rules

- **OP1.** Emigration draws come from a tagged child stream of the mortality module (as `baselines/fertility.py:24–28` does for births), so turning emigration off leaves every death draw unchanged. A person can die or emigrate in a year, never both: death is drawn first, as now, and emigration only among survivors.
- **OP2.** The second parent is the mother's spouse or partner in the authoritative marital state, of any sex; an unlinked newborn carries one of a registered list of reasons (unpartnered mother, partner outside the roster, partner unknown). The sex ratio is pinned from NCHS before any gate. No newborn reads an adult process until a later milestone admits it.
- **OP3.** As #218 §4–§5: no cloned future; a pre-entry state is a stock proxy until a registered stock-to-arrival bridge exists; the 2014 file is read only for scoring after lock; the five-year pooled ACS file is never used. A real-data schedule needs the universe bridge.
- **OP4.** No death is relabeled as emigration or the reverse; a spouse who emigrates never widows the partner who stays (§7). Whether a person who entered this year can also emigrate this year is frozen at OP0.1 (#217 §8, decision 2, left it open).
- **OP6, OP9.** As #217 §4: two immutable projections from the same inputs; whole-unit selection for events, a scalar for covered wages; no person weight changes; the gate verdicts of the unaligned run cannot move.
- **OP7.** Its arms and its 2013-vintage inputs are frozen at OP0.1; any arm fed realized aggregate controls is labeled as such and admits composition only.
- **OP8.** Sub-parts (b) and (e) build on Track B's admitted law and may not change it. The builder of (e) satisfies ruling d1659's independence requirement (§8, "Governance risks"). Sub-part (a) follows B4's schemas as B4 declares them; where B4 has not declared a schema, (a) delivers the #218 §4.8 packet and B4 maps it.
- **OP10a, OP10b.** The horizon record lists every component's fitted support and its declared rule outside it; a run that queries a component outside its support without a rule is refused.
- **OP11b.** As Track B §5.4 for B7: a sealed comparator with two transcriptions, a blind builder under an updated RESTRICTED-FILES, a hashed forecast before the run, and a one-shot at a registered commit.
- **OP12.** It runs on the aligned population, so it scores the aligned production scenario: what passes is "aligned totals match SSA's", not "the unaligned laws produce SSA's totals". The registration states this, and the unaligned totals are published beside it.

## 6. Interfaces

### 6.1 Track B: H, B4, J, and also I and B7

This lane edits nothing in `track_b/`; it asks Track B for the interfaces below and supplies the ones Track B §3.4 says it needs. §3.5 lists what OP8 delivers to each Track B milestone. Where a request lands inside a Track B milestone not yet built, Track B decides; nothing here changes Track B's prices.

**H, the history recorder (Track B §3.1: 2010–2030; entry and death; labor, covered and RET-countable earnings separate; zero and missing distinct).**
- *This lane needs from H:* a history opened at entry for any entrant, with pre-entry years carried as the convention Max picks (§10, decision 4) and never silently zero; emigration recorded as its own exit, distinct from death, so that an insured emigrant's record survives; a horizon end year that is a parameter rather than a fixed 2030, so that OP10b does not need an H v3.
- *This lane supplies to H:* every entrant's `entry_kind`, entry year and exit records (OP1), and the opened history and quarters of coverage of OP8(c).

**B4, the forward projection successor (Track B §3.1, §3.4).**
- *This lane needs from B4:* forward marital and household adapters that admit people who join the risk set after the start (newborns ageing into marriage, immigrants entering married or single), so that a second-parent link can come from a marriage formed after the start (OP2); widowhood that ignores exits by emigration; and B4's coverage declaration naming which entry kinds it covers.
- *This lane supplies to B4:* OP8(a)'s starting states in B4's schemas, built from OP2's and OP3's packets, while B4 is built, so that B4 can declare open coverage; and, once OP8's gates pass, the admitted entrant initialization B4 needs before it claims that coverage.

**J, joint validation (Track B §3.4; estimands frozen at B0.2 and ratified before B3 registers).**
- *This lane asks:* that J's B0.2 record declare closed or open coverage and, if closed, report the weight of entrants it excludes from each denominator. If OP8 is not admitted by then, J is closed-coverage, and any B7 target needing open coverage is blocked by `ENTRANT_INIT_UNADMITTED` (Track B §7) until OP8 passes.

**I, the monthly calendar (Track B §3.4).** I's event journal records entry and death; this lane asks that it also record emigration as a dated exit, and adopt the seam's entry-year convention (§2.3) or register its own.

**B7 (Track B §3.4's scope matrix).** "Population" in the scope matrix includes open or closed coverage; §3.5 says when B7 can declare closed coverage.

**G (`track_b/gross_benefits.py`).** Child benefits need both parents' records; OP2(a) supplies the links G reads.

**The insured-status rule (Track B's rules lane, under d1802; a separate PR once #530 merges).** Its scope, as the coordinator relayed it on 21 October 2026: quarters of coverage; fully, currently and disability insured, including the special rules before 31 and for blindness; and the date last insured, designed for B6a's person-month risk set. OP8(d) consumes it and does not change it. What OP8(d) needs from it:

1. **Quarters of coverage as an input.** Besides computing quarters from covered earnings, the rule accepts a person's quarters of coverage by year (0 to 4) directly, so that OP8(d) can supply quarters for years whose earnings are not observed.
2. **Elapsed years from the birth date, not the entry date.** The fully-insured test counts the years elapsed after 1950 or, if later, after the year the person turned 21 (Social Security Act §214(a)), wherever the person lived. An immigrant who arrives at 45 therefore faces the same count as a native-born worker of the same age. The rule takes the birth date and evaluates at a stated month, as B6a needs.
3. **Monotone in quarters.** Adding a quarter of coverage in any year never takes away any insured status and never makes the date last insured earlier. The statutory tests are all thresholds on counts of quarters, so this holds by construction; the rule's tests should state it as a property, because OP8(d)'s bounds (point 5) rely on it.
4. **An optional input for credits from outside US coverage,** empty by default, so that a later treatment of totalization agreements (§3.6) can add credits without changing the rule.
5. **How the pre-entry convention enters the count.** OP8(c) labels every year before the entry year as unavailable; the entry year and later years carry the quarters credited from earnings recorded after entry (from 1978 on, quarters are credited from a year's covered earnings, up to four, as Track M's crediting code records at `min_benefit_track_m/coverage.py:16–19`; so the entry year needs no month). OP8(d) then calls the rule twice per evaluation, once with every unavailable year filled with zero quarters and once with four, and reports:
   - **insured** if the zero-filled call says insured;
   - **not insured** if the four-filled call says not insured;
   - **undetermined** otherwise, with both results and the date last insured under each.

   Max's choice for decision 4 (§10) picks what is published. Under the **zero convention** (a first-entry assumption), the zero-filled result is the status, and nothing is undetermined. Under the **censored convention**, undetermined entrants stay outside claiming and DI (as `entrant_domains.py` keeps them now) and are counted, never treated as uninsured. The rule itself needs no knowledge of either convention.
6. **Newborns and emigrants.** A newborn has no pre-entry years; its quarters come from its own earnings under OP8(e). An emigrant's quarters stop accruing at exit; the rule can still evaluate the emigrant's status and date last insured at later months, which OP12 needs to count insured emigrants.

### 6.2 The Microcosm start (`docs/plans/microcosm-start.md`; d947 parked)

- **Start-agnostic machinery.** OP1 to OP6 run on any start: a closed PSID cohort, OP5's ACS start, or Microcosm's frame. National claims (OP12) need a representative start; that is the Microcosm start's job, and d947 decides whether its registration posts.
- **What d947 being parked blocks.** Nothing in the demographic phase: its gates use OP5's ACS start. In the economic phase, OP12 needs the Microcosm start's gate 3 to have passed.
- **Weights.** The Microcosm start holds each person's start-year weight fixed and notes that the projected population closes until births and immigrants enter (`microcosm-start.md:453–456`). This lane keeps fixed trajectory weights: newborns take the mother's weight (§2.2), immigrants take the control-scaled donor weight (§2.3), and alignment selects people rather than reweighting them.
- **Gate 3.** Its cells score the first projected year's growth in retired- and disabled-worker counts and average benefits (`microcosm-start.md:351`). OP1's harness keeps entrants out of claiming with `EntrantClaimingAdapter` until OP8 lifts the exclusion, so entrants do not touch those cells. This lane recommends that gate 3 run closed, as drafted, with an open-population variant published report-only beside it.
- **One convention to reconcile.** For immigrants already in the frame, the Microcosm start begins a history no earlier than a year drawn within the person's entry-year group (`microcosm-start.md:492`; the registration draft cuts histories at entry, `microcosm-start-registration-draft.md:81`). For scheduled entrants, `entrant_domains.py:210–228` treats pre-entry US covered earnings as censored and blanks benefits to missing. The two treatments differ. One registered convention should cover both populations (§10, decision 4).
- **Frame immigrants as donors.** The frame carries year of entry, nativity and citizenship (`microcosm-start.md:117`), so its recent arrivals are a candidate second donor pool; OP0.1 compares it with the ACS's.

### 6.3 Moving the engine into Microcosm (#412)

Issue #412 maps alignment onto per-year REWEIGHT nodes, which would change weights, while this design and #217 select whole people at fixed weights. Both can coexist: selection now, on the existing engine; a REWEIGHT implementation later must reproduce the same aligned margins and publish the same displacement. #412's "entry without lineage" amendment should take this lane's `entry_kind` and donor-provenance columns as its row markers.

### 6.4 Other lanes and governance

- **Insured status.** The ledger row is *None* today. Under d1802, Track B's rules lane builds the rule as a separate PR once #530 merges; OP8(d) and OP12 consume it through the §6.1 interface, as Track B's B6a does.
- **RESTRICTED-FILES.** These entries bind this lane:
  - *A-COLA (Registration 18):* its builders read no Trustees Report table of cost, income or balance rates and, from the committed IV.B4 snapshot, only one beneficiary count. OP9's builders read IV.B4's covered-worker rows, so under that rule they cannot also be A-COLA builders.
  - *NASI follow-ups:* Urban's published DYNASIM output and MINT option tables for the five reforms are restricted to validation-only comparator lanes. OP11b's builders never open them.
  - *B2 outcome files (2026-10-18 entry, enforced in code by #549):* successor designs blind to B2's outcome exclude them. OP8's sub-parts (b) and (e) build earnings components, so §8 sets who may build them.
  - *B0.2 and the B2 successor design (2026-10-21 entry):* B0.2's lanes and the successor-design lanes may not open each other's folders, lane clones or (for successor roles) draft PR #554 beyond its title. OP8(e)'s builder takes one of those roles or neither, never both. This lane has opened neither side's folders.
  - *U2 step-4 run 2 outputs (2026-10-21 entry):* restricted for everyone except their `MANIFEST.md`. Nothing in this lane reads them.
  - *Transcripts, scratchpads and `~/.subfleet/` folders* other than a lane's own stay closed to every lane.

## 7. Invariants and property-based tests per component

Each invariant becomes a Hypothesis property test on invented data beside the example tests, as the repository's rule for load-bearing logic requires. Two are differential tests between independent implementations.

- **Stock-flow (OP1).** For every year: people at the end = people at the start − deaths − emigrants + births + scheduled entrants, exactly in counts; and the same in weights, within the summation residual `reconcile_period` reports. Every addition carries a known `entry_kind`; every exit carries one exit kind; no person exits twice; no ID is reused (`validate_projection_allocator` on the exact metadata).
- **Emigration coupling (OP1, OP4).** With emigration off, the survivors equal the closed run's exactly. No person both dies and emigrates in one year. Raising every emigration hazard never lowers emigrant weight in any cell (monotone, with draws fixed).
- **Horizon prefix (OP1).** Under the registered-horizon convention, the slice for year t is identical across runs that differ only in the horizon read; a production request with any other end year is refused. The committed evidence (§2.9) is the failing case this property guards.
- **Determinism and order invariance (all).** The same inputs and seeds give byte-identical output; shuffling roster rows changes nothing.
- **Newborn packet (OP2).** Each newborn has exactly one mother on the roster in its birth year; a linked second parent is on the roster, is not the mother and is her spouse or partner in that year's authoritative state; age 0 and birth year equal the year; weight equals the mother's; adult-domain markers are out of domain.
- **Live-roster fertility (OP2, differential).** On a closed panel, the live-roster kernel reproduces the cached candidate-16 kernel's births exactly.
- **Entrant schedule (OP3).** Scaling every control by k scales every entrant weight by k; a zero control adds no rows and consumes no IDs (already true of `build_entrant_schedule`, `entrant_schedule.py:282–294`); the donor composition is reproduced exactly; no entrant's pre-entry covered earnings are zero unless the registered convention says so.
- **Relational consistency (OP4, OP6).** Every death of a linked spouse produces exactly one widowhood; no emigration produces one; an aligned death updates relations exactly as a drawn death does.
- **Alignment (OP6, OP9).** The unaligned artifact is byte-identical whether the aligned producer is importable or not; the aligned margin is within its selection-resolution floor plus tolerance; `build_alignment_displacement` receives exactly equal keys; no person weight changes; an empty target bundle reproduces the unaligned run.
- **Stable population (OP10a, differential).** With constant single-age fertility and mortality and no migration, the expected age-sex distribution in each year (the mean over seeds) agrees, within Monte Carlo error, with a two-sex Leslie projection from the same start and rates under the engine's timing conventions (§2.2); and the long-run growth rate approaches the logarithm of the Leslie matrix's dominant eigenvalue. The micro engine and the matrix are the two implementations compared.
- **Extrapolation (OP10a, OP10b).** No component is queried outside its fitted support without a declared rule; the refusal is tested.
- **Insured-status bounds (OP8(d)).** The zero-filled status never exceeds the four-filled status; "undetermined" occurs exactly when they differ; under the zero convention nothing is undetermined; an entrant with no unavailable year gets the same status from both calls.
- **Entrant economics (OP8).** Earnings are finite and nonnegative; pre-entry years are never filled with zero unless the registered convention says so; the hand-off at 25 lands inside the forward law's support; insured status is never computed from an unavailable year.

Counterexamples are executed and minimized before anyone calls them bugs.

## 8. Risks and kill criteria

### Blocking rule

Track B's rule applies unchanged (Track B §7): required-source unavailability, unresolved exposure, inadequate precision, unsupported critical configurations, or a failed gate or required regression test block the corresponding admission and the milestones that depend on it. Fallbacks register before candidate outcomes. Failed or unsupported cells stay reported, and removing them cannot manufacture a pass.

### Named conditions and what each stops

| Condition | Trigger | Stops |
|---|---|---|
| `ACCOUNTING_IDENTITY_FAIL` | A stock-flow identity fails in any year | Every OP run until fixed |
| `ID_OR_STREAM_COLLISION` | An allocator could reuse an ID, or a production run's end year differs from its registered horizon | That run |
| `CONTROL_SOURCE_UNAVAILABLE` | A target or control (OACT single-age fertility or population, V.A2 rows) cannot be pinned | That margin stays `not_available`; no "aligned to OACT" claim for it |
| `UNIVERSE_BRIDGE_UNRESOLVED` | No registered bridge from the Social Security area to the roster | Real-data immigrant schedules and every stock claim |
| `DONOR_SUPPORT_THIN` | `gate_imm`'s cells fail support floors after the registered pooling ladder | Gated composition claims for those cells; they stay report-only |
| `EMIGRATION_UNIDENTIFIED` | OP0.1 finds no admissible holdout for exits | Composition claims by nativity and duration; totals stay aligned |
| `ALIGNMENT_DISPLACEMENT_EXCESSIVE` | Displacement above its corridor in a registered number of consecutive years, or growing through the horizon | Release of that aligned margin pending model review; a second registered review that finds the same blocks any claim past 2030 that depends on the margin until its law is refit |
| `ENTRANT_INIT_UNADMITTED` (Track B §7) | OP8's `gate_entrant_earn` or `gate_young_earn` fails or is inconclusive | Targets requiring open-population coverage for the states that gate covers |
| `INSURED_STATUS_ABSENT` | Track B's insured-status rule is not merged, or does not meet the §6.1 interface | OP8(d) and its lifting of entrant exclusions; OP12 |
| `HORIZON_NOT_LICENSED` (Track B §7) | The horizon record or the long backtest fails its registered limits | Any claim past 2030 beyond a conditional projection |
| `EXTRAPOLATION_UNDECLARED` | A component is queried outside its fitted support with no declared rule | That run |
| `SUCCESSOR_EXHAUSTED` (Track B §7) | Two independently justified B2 successors fail | The economic phase pauses; the demographic phase continues |
| `GATE_FAIL_OR_REGRESSION_FAIL` | Any registered OP gate fails | That admission and its dependants; the failure is published with no seed selection or tolerance relief |

### Attempt ledger

Track B's cumulative attempt ledger applies by mechanism and gate family: open-population fertility, immigrant composition, emigration, demographic composition, entrant earnings and young-adult earnings each count separately. Renaming a module does not reset a counter; two failed successors pause a mechanism pending new evidence.

### Risks most likely to slip

- **Track B's B2 successor.** Every economic milestone waits on it (§3.4), and two failures pause the earnings mechanism.
- **Granular demographic targets.** If OACT's single-age fertility and population are neither public nor obtainable, alignment uses registered bridges or stays partial.
- **The universe bridge and V.A2's semantics.** The temporary-or-unlawfully-present inflow counts people who remain to year-end (`entrant_schedule.py:365–371`), and adjustments of status move people between categories without moving them in or out.
- **ACS stock proxies.** Recent arrivals in the ACS are survivors and stayers observed after entry, not arrivals (#218 §2.2).
- **Weight concentration and run size.** Seventy-five years of an open population on a Microcosm-sized frame is a larger run than any so far; OP1 measures memory and runtime on invented data at full size before OP10a.

### Governance risks

- **B2 outcome exposure.** This design's author read the parity ledger, which states B2's result, so the author is outcome-aware. Ruling d1659 requires a B2 successor's change to rest on evidence independent of that result. OP8's sub-parts (b) and (e) do not alter Track B's law, but (e)'s hand-off state would feed it. So OP8(e) is built either inside Track B's successor lane under its blinding, or by a lane that d1659's terms clear; the coordinator assigns it (§10, decision 6).
- **Methodology principles are Max's.** §10 lists them; none is settled by this document.

## 9. Staffing and scope assumptions behind every estimate

- **Unit of effort.** One engineer-day is one day of reviewed output; one agent lane delivers about 4 engineer-days a week. Every lane-week figure is the engineer-day figure divided by 4.
- **Two OP lanes** in each phase, D1 and D2 in the demographic phase and E1 and E2 in the economic one, separate from Track B's two lanes. Elapsed figures assume both run at once.
- **Every range is an engineering judgment,** not demonstrated throughput. The sub-splits inside OP2, OP3, OP4 and OP8 are mine. Track B's figures in §3.4 are Track B's.
- **Comparison with design B's B8.** B8's 40–70 d covered "2032/2050 and population extension" with income and wealth gates. This design prices more (births v2, emigration, demographic and labor alignment, six gates, the horizon record and long-horizon comparisons) and excludes income and wealth. The difference is scope and the M6 assembly finding (§2.4), not a re-estimate of B8's items.
- **Excluded:** review and registration queues; Max's, the coordinator's and referees' time; data-access time for any restricted or requested source; Track B's insured-status rule; the items of §3.6; Track B's milestones; the Microcosm start's tasks; comparator-lane work for sealed comparisons; research after a failed gate.
- **Data.** ACS, NCHS and Census sources are public and assumed downloadable; SSA pages need the capture user agent. PSID inputs are assumed available locally for registered steps only. This was not verified for ACS and NCHS in this run.

## 10. Decisions for Max

1. **Approve the two-phase structure and the demographic phase now (71–105 d, estimate)?** Recommended: yes. Price the economic phase now, as here, but approve it when a B2 successor passes and Track B's B0.2 freezes J's record.
2. **Size immigration by the Trustees' gross positive inflow, with emigration as a separate exit law, rather than by net change?** Recommended: gross plus exits (#218's ruling; `entrant_schedule.py:37–42`). Net change has no person-level composition.
3. **Align by selecting whole people at fixed weights, keeping the unaligned run as the scored object?** Recommended: yes, as M6's decision 9 and #217 rule. Per-year reweighting (#412's REWEIGHT nodes) can come with the move into Microcosm if it reproduces the same margins and displacement.
4. **One convention for immigrants' pre-entry US covered earnings, applied to frame immigrants and to entrants alike:** zero under a first-entry assumption with a registered return-migration sensitivity, or censored (missing) with benefits suppressed until a bridge exists? Recommended: censored for gates and published benefits, with the zero convention as a labeled sensitivity, because a reported year of entry does not identify first entry (`entrant_domains.py:56–62`, `:215–219`). Under the censored convention, insured status is reported as determined only where both bounds of §6.1's interface agree; under the zero convention it is the zero-filled result.
5. **Horizon admission past 2030:** every projected year past 2030 is published as conditional on named assumptions, with drift diagnostics, and never as a validated forecast; DYNASIM comparisons at 2050, 2065 and 2070 are registered, report-only, and blind. Recommended: yes. This is a methodology principle.
6. **Who builds OP8(e) (earnings at 16–24 and the hand-off to Track B's law)?** Recommended: Track B's successor lane, under its d1659 blinding, priced here; otherwise a lane d1659's terms clear.
7. **Include `gate_pop` (OP7, 6–8 d)?** Recommended: yes. It is the only scientific test of the population's composition over time; the rest of the demographic phase is conformance or alignment.
8. **Emigrants and benefits paid abroad:** in v1 emigrants leave the roster and OP12 reports insured emigrants as a named gap. Recommended: yes for v1; price an abroad ledger before any national-cost claim (M7).
9. **The registered-horizon convention (§2.9):** every production run projects to the baseline's last year, and shorter horizons are read as prefixes. Recommended: yes; it costs compute, not engineering.

## 11. Files read, commands run and exposure

**Restricted-files list.** I read `~/microcosm-launch-evidence/dynasim-parity-20260909/RESTRICTED-FILES.md` first, in full, and opened nothing it lists. For revision 2 I reread its two entries dated 21 October 2026 (the B0.2 and B2-successor separation, and the U2 step-4 run 2 outputs); I have opened none of the folders they name, and I read only the title of draft PR #554.

**Read in this run.**
- *Instructions and plans:* `CLAUDE.md` (repository and parent); `docs/parity-ledger.md`; `docs/plans/microcosm-start.md`; `docs/plans/microcosm-start-registration-draft.md` (search matches only); Track B design revision 3 (§1–§10); design B's milestone table (`phase2-20260927/out/trackb-b.md`, lines 85–110); `docs/entrant-seam.md`; `docs/baselines.md` (lines 470–530).
- *Source:* `engine/loop.py`, `engine/entrant_schedule.py`, `engine/entrant_domains.py` and `baselines/fertility.py` in full; `engine/steps.py` (lines 100–209, 380–561); `engine/marital.py` (lines 338–404 and a search); `engine/assembly.py` (lines 1–30, 170–447); `engine/panel_builders.py` (lines 1–40 and a search); `engine/support.py` (lines 1–40, 215–260); `engine/rng.py` (lines 1–180); `engine/accounting.py` (lines 1–140); `engine/accounting_history.py` (lines 1–60); `engine/earnings_domain.py` (lines 1–25 and a search); `harness/m6_reporting.py` (lines 300–415); `baselines/base.py` (lines 1–80); `baselines/tr2026_intermediate.py` (lines 1–134); `baselines/cbo2026_long_term.py` (lines 1–45); `baselines/track_a.py` (lines 15–60); `baselines/__init__.py` (lines 15–40); `data/tr2026.py` (lines 1–60 and a search); `ss/statutory_aime.py` (lines 130–150); `scripts/first_estimates_birth_evidence.py` (lines 126–200 and a search); `scripts/fetch_nchs_asfr.py` (lines 1–25); `tests/baselines/test_invented_smoke.py` (lines 223–300); `min_benefit_track_m/coverage.py` (lines 1–30) and a search of `min_benefit_track_m/policy.py`; search matches only in `uk/household_transitions.py` (lines 747–851), `harness/m6_runner.py` (lines 1027, 1212, 1249), `tests/estimates/test_birth_evidence_artifact.py` (line 68) and `tests/track_u2/test_u2_isolation.py` (line 242).
- *Contracts and records:* `gates.yaml` (lines 995–1010, 1330–1340, 2895–2925, 5370–5450 and searches); `runs/gate_m6_candidate3_v1.json` (fields whose keys mention entrants, alignment, births or immigration); `data/external/tr2026/provenance.md` (lines 1–36 and a search); `data/external/cbo2026/provenance.md` (lines 25–60) and the top-level keys of the two CBO JSON files.
- *GitHub:* issues #412 and #151; PRs #217 and #218 (bodies, and their design documents fetched from the PR heads: #218 lines 1–315, 458–520 and 824–1124; #217 lines 1–330 and 652–857).
- *Web:* TR2026 Tables V.A2 and V.A3 (titles and column headers only, fetched 21 October 2026 with the `Wget/1.21.4` user agent).

**Commands run.** `docs/design/open_population_evidence/horizon_dependence.py` on invented data (output committed beside it); text searches of `src/`, `scripts/`, `tests/`, `docs/` and `data/external/` for migration, alignment, natality and ACS terms.

**Exposure.**
- No real-data outcome was computed. No restricted file, Urban document, DYNASIM output, MINT table, Trustees cost table or B2 outcome file was opened.
- The parity ledger states B2's scored result, so this design's author is outcome-aware for B2 (§8).
- Printing `runs/gate_m6_candidate3_v1.json`'s entrant fields showed per-draw newborn counts and the person IDs of mothers whose scheduled births were dropped. They are committed artifact values; nothing from them but the ledger's 316 appears here.
- The closed PRs' design documents quote the 2026 V.A2 values and describe DYNASIM, MINT and PENSIM methods from public documents. This design uses none of those values.
