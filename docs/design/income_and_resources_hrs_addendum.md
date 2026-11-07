# Income and resources: HRS public-file addendum

**Design only.** This addendum proposes using public HRS files in five rows of the income-and-resources design (`docs/design/income_and_resources.md`, "the design" below). It builds nothing, downloads nothing and registers nothing. It joins the design only if Max approves it; until then the design stands as merged. Section numbers such as "design §5" refer to the design.

## 1. Summary

- **What HRS adds.** HRS cell families in the wealth and pension gate, WP-G, at ages 51 and over, registered separately from its PSID families and admitted only with a registered standardization procedure (§4.1); a report-only external check for WP8; and, for SSI, either a third take-up training population (option A) or a third held-out population for the SSI gate, SSI-G (option B).
- **Recommendation: option B,** if IR0 finds a powered, harmonized HRS cell for SSI-G (§4.4). HRS then stays truth-only in every row, so no HRS cell is ever both a training input and gate truth.
- **Records stay out of agents' reach.** A trusted worker reads the files and releases only allowlisted metadata, row counts and cell statistics under a frozen release policy. Running it under a separate operating-system account is recommended and is Max's choice (§3, §9).
- **Price.** 11.5–19.5 engineer-days with option B (11–18.5 of them in tier 1), or 11–18.5 with option A, including the separate account (1–1.5 d). The base rises from 182–278 to 193.5–297.5 days (B) or 193–296.5 (A).
- **Critical path.** The three tier-1 gates' first attempts publish after 45–68.5 engineer-day equivalents under option B, and 44.5–67.5 under option A, against the design's 42–62 (§6.2).
- **Unchanged.** The HRS–SSA restricted products stay excluded, and design §12 item 7 (whether to apply for them) stands as written.
- **Facts this addendum does not verify** decide whether parts of it survive: whether the public files carry an SSI receipt item separate from Social Security and SSDI; whether they carry the weights and design variables a floor needs; which waves' items have reference periods wholly after WP-G's 2013 information cut; and whether each cell's items and crosswalks exist. D6, the reader, checks each first, and §8 says what each failure stops.

## 2. Sources and access

HRS use follows the project's data-access record: public HRS files only. D6 starts when the files are in place in the data directory the project names. Facts below come from the lane's source catalog (`EV/income-resources-20261021/research/data-sources.md`, §§7–9, verified 22 October 2026); unverified ones are marked.

| Product | Content the addendum uses | Years | Status |
|---|---|---|---|
| RAND HRS longitudinal file | Harmonized income, wealth, demographic, employment and retirement measures, for example household income `HwITOT` and wealth `HwATOTA` | Final releases 1992–2020 and the 2022 early release | Current analytic record count unverified |
| RAND HRS detailed imputations | IRA withdrawals, including items `xQ177_1–3`, labelled "IRA MONEY MINIMUM WITHDRAWAL" | 2002–2020 | Whether these identify every required minimum distribution is unverified |
| HRS core | Sections J2 (pensions), J3 (retirement and Social Security), Q (assets and income) and R (asset change) | Biennial; 2024 Core Early V1.0, released September 2026, about 14,400 respondents and 10,800 households | Question-specific income periods differ from interview years |
| Employer-sponsored pension wealth, current jobs | DB wealth from self-reports combined with employer plan-document rules; DC wealth from balances and imputations | 1992/1998, 2004, 2010 and 2016 (2016: about 4,200 respondents) | None after 2016 verified |

**Access.** This addendum uses public HRS files under the project's data-access record. The catalog documents ASCII, SAS, SPSS and Stata formats for HRS; exact formats for every current RAND package and registration turnaround remain unverified.

**Not used.** The HRS–SSA restricted products (summary and detail earnings, benefits and SSI records; catalog §9) stay excluded. Usable public-file careers for the design's lifetime-earnings measure are unverified, so this addendum registers HRS cells by birth cohort, age band and sex only and adds no lifetime-earnings-group evidence. The design permits labelled labor-earnings groups before CE5; administrative linkage is not a prerequisite.

**Also unverified, and checked first in D6:**

1. Whether the public files report SSI receipt and amounts separately from Social Security and SSDI. Both SSI options need it.
2. Whether the public files carry the person and household weights, strata and clusters that design-based resampling needs (design §7.1).
3. The HRS sample's entry ages and refresh cohorts, which decide which birth cohorts each wave represents.
4. The reference period of each item used, which decides which waves count as held out (§4.1).

## 3. Data-handling rules for HRS files

These are the project's rules for every HRS file and for every agent, lane and session that writes code touching them.

- **Storage.** HRS files sit outside every repository, worktree, scratch folder and Subfleet job folder, in one data directory the project names. Code finds it through `POPULACE_DYNAMICS_HRS_DIR`. There is no default path: if the variable is unset, the reader refuses. No HRS path goes into a prompt for a lane that can open files in its workspace.
- **What reaches an agent.** File and column metadata (headers, names, types, value labels, codebooks), row counts, and aggregates over two or more records. Never an individual record: no row printing, no per-person values in logs, test output, fixtures, commits, PR bodies, issue comments or Subfleet prompts, and no row-level diffs.

These rules bind every agent. A storage location does not stop a process that can read the file system, though, and some aggregates over few records reveal a record: a maximum does, and so does a mean of two records when one is known. So D6 enforces a stricter boundary in code.

- **Execution.** A trusted worker reads the HRS files. In the recommended setup it runs under a separate operating-system account that alone can read the data directory, and agent processes and their tools cannot read that directory, the worker's environment, its raw outputs or its temporary files. Creating that account changes the machine that holds the files, so it is Max's choice (§9). Without it, the worker runs under the agent's own account, and the boundary rests on the rules above, the interface below and the tests in §7. This addendum does not call that arrangement enforced isolation.
- **Release interface.** The worker releases only allowlisted metadata, row counts and cell statistics approved under a release policy that IR0 freezes. The policy sets the minimum number of distinct contributors per cell, suppression and complementary-cell checks, and controls on overlapping releases. Until IR0 freezes it, the worker applies a provisional minimum of ten distinct contributors. The interface has no row-returning operation and no arbitrary row or aggregate query. It never releases a minimum or a maximum, and it releases a quantile only as the policy's quantile rule allows. Raw records, per-person values and unsanitized diagnostics never cross the boundary. A cell-count threshold alone does not establish a disclosure guarantee.
- **Errors.** The worker converts every failure into a fixed diagnostic schema that holds only approved file identifiers, column identifiers and error classes. It releases no original exception object, chain, traceback or local variables.
- **Tests.** Synthetic fixtures use the verified schema. Tests that inspect real-file metadata run in a new `integration_hrs` tier. D6 adds the tier marker and an HRS source indicator to `tests/conftest.py`, explicitly skips these tests when `POPULACE_DYNAMICS_HRS_DIR` is unset, and updates `tests/tier_counts.json`. CI runs every tier (`.github/workflows/tests.yml` has no marker filter), so the skip must be in each module, as the PSID integration modules skip on unstaged files (for example `tests/data/test_family_income_integration.py:19–24`).
- **Publication.** IR0 independently freezes the HRS release and publication thresholds. ADR 0002 remains proposed and provides an internal precedent of n ≥ 10 for committed aggregate tables (`docs/adr/0002-uk-extension-ukhls.md`); it does not establish an adopted HRS rule.
- **Sequencing.** Design §7.2's U2 sequencing rule extends to HRS. HRS income, wealth and SSI aggregates for the 1946–55 birth cohorts near age 67 are the same kind of realized outcomes that rule protects for the PSID. So until U2's one-shot result is posted, no milestone publishes, or posts to GitHub, an HRS statistic for those cohorts; a gate that must publish earlier first has its outputs listed in `RESTRICTED-FILES.md`, an entry the orchestrator makes. IR0 also records any agent that sees such an aggregate as exposed for U2's forecaster and checker.

## 4. HRS's role in each row

The source-role rule applies: each HRS cell is gate truth or a training input, never both. This addendum makes HRS truth-only everywhere (option B) or truth-only outside SSI4 (option A).

### 4.1 WP-G (WP5): HRS cell families at ages 51 and over

- **Proposed cells.** WP-G's families (design §3.2), restricted to ages 51 and over, by birth cohort, age band and sex. D6 must verify each cell's required items, ownership, reference periods and measurement crosswalk before IR0 admits it; unsupported measures remain unavailable:
  - pension coverage on the current job, DB and DC;
  - DB benefit receipt and amounts, from the core income sections;
  - DC and IRA balances, and withdrawals from them;
  - asset income, its receipt and amounts;
  - net worth, and the share whose countable liquid assets sit below SSI's limits.
- **Held-out waves.** WP-G's candidates use information through the 2013 wave. The catalog explicitly lists candidate RAND waves 2016–2022, core waves 2016–2024 and the 2016 pension-wealth product; the inspected detailed-imputation documentation ends in 2020. Additional waves require D6 verification. IR0 admits an item only when its reference period falls wholly after 2013.
- **What the comparison means.** WP-G scores the model on the PSID 2013 roster's realized support. An HRS cell is a different sample of the same birth cohorts, and its observations can differ from the PSID's through population composition, survival, household structure and measurement. So an HRS cell tests the projected distribution at the population level, not unit by unit, and only through the standardization below.
- **Floor.** WP-G's PSID-realized-support floor is unchanged. HRS comparisons remain report-only until IR0 specifies a common estimand, an observation operator and a transport or standardization procedure that aligns model outputs with the HRS target. That procedure is registered before any outcome is computed. The HRS families, registered separately from the PSID families, estimate sampling variation through within-HRS design-based replication, built after registration pins the commit (design §7.3). The PSID–HRS realized discrepancy is reported separately and never enlarges the acceptance tolerance. Without valid survey-design uncertainty inputs (§2, item 2), HRS cells are not admitted.
- **Bite and order.** IR0 freezes WP-G's bite-check cells and conjunction across the PSID and any admitted HRS families. After registration and the truth-only floor, M0 is scored first. If the registered bite condition triggers, WP-G stops before M1 is scored and needs a prospective rescope under a new registration. No cell is removed after its null or candidate results are seen.
- **Power.** IR0's power audit partitions HRS cells into gated and report-only before any candidate result, like every other cell.

### 4.2 WP8: a report-only external check

HRS joins the SCF, the Financial Accounts, Form 5500, SOI and SIPP as a report-only check on a representative population (design §3.2). The RAND withdrawal items give a report-only check of WP2's RMD ages; because whether they identify every required distribution is unverified, that check is labelled descriptive.

### 4.3 WP4: unchanged

M1 trains on PSID donors only. The 2016 pension-wealth product never enters WP4's training. Its DB wealth remains report-only unless IR0 defines and registers a comparable model output and observation operator.

### 4.4 SSI: two options

**Shared by both options.** Frozen-state potential eligibility must be computable for HRS units, so SSI0's source-to-input contract gains an HRS population column. The contract (`ssi0-v1`, PR #573) has 41 engine rows and 12 context rows, each with decisions for PSID, SIPP and Microcosm (`src/populace_dynamics/income_resources/ssi/input_contract.json`). Version `ssi0-v2` adds an HRS decision for each of the 53 rows: an HRS item, a registered assumption or a refusal. A refused input refuses the case and keeps it in every denominator (design §3.3). SSI-G's cells score predictions for HRS units themselves, from that column, so unlike WP-G's they need no transport; IR0 still registers how the HRS receipt item's reference period maps to SSI-G's annual-state receipt.

**Option A: HRS trains SSI4.** HRS units become a third training population for SSI4's take-up model, beside SIPP and the PSID, inside the training partition IR0 freezes. IR0 freezes roles jointly across gates at the item, wave and cell level, including eligibility covariates; no HRS cell used by SSI4 may also serve as WP-G truth.

- Work: harmonizing HRS's SSI receipt item and covariates with SSI4's; adding HRS to the training partition; refitting.
- Effect on SSI-G: none. HRS cannot then be truth for SSI-G.

**Option B: HRS is held out for SSI-G.** One or more held-out HRS waves become a third held-out population for SSI-G's receipt-propensity cells (the aged by age band, sex and marital state), beside the PSID and SIPP.

- Work: HRS cells in SSI5's registration package; after registration, their truth-only floor and age-and-sex null; SSI5R alone scores SSI4's model once on them and publishes.
- Effect on SSI4: none; it trains on SIPP and the PSID only.

**Recommendation: option B.**

1. **It adds an external test.** Option B tests a fixed SIPP/PSID model in HRS. Option A adds training data while retaining the PSID/SIPP held-out gates. IR0 must compare usable aged SSI counts, covariate overlap, measurement harmonization and gate power before claiming which supplies stronger evidence. Prefer B if a powered, harmonized HRS gate is feasible.
2. **It keeps one role for HRS across the lane.** HRS is truth in WP-G under either option; option B keeps it truth in SSI too, so no reviewer has to track an HRS cell that trained one model and scores another.
3. **It preserves an initial external test.** After B's gate runs, its HRS outcomes are exposed. A later version may train on those cells only after retiring them from independent predictive truth and recording their exposure. The revised model needs genuinely unused validation data; reused exposed cells supply retrospective regression evidence only.
4. **It matches the first admission.** SSI3 admits the aged only, and HRS samples older people and their spouses.

If IR0 finds no powered, harmonized HRS cell for SSI-G, the HRS SSI cells are report-only under option B, and option A remains available as a new registered version. This addendum has no count of aged SSI recipients in any of the three samples, so it does not claim A would improve SSI4's fit. Misreporting of SSI as Social Security stays a named limitation in both options. Public HRS SSI reporting accuracy and its comparability with PSID and SIPP remain unverified. The excluded SSA-linked records cover consenting/linkable respondents; the catalog does not establish a correction for the full HRS population. SSI-G reports each population's cells separately.

## 5. Changes to the design's tables

### 5.1 New row in design §4.1

| Id | Tier | Deliverable | Verification or gate | Effort estimate (d / lw) | Depends on | Unlocks |
|---|---|---|---|---|---|---|
| **D6** | 1 | HRS public-file reader, run by §3's trusted worker: RAND HRS longitudinal file and detailed imputations for the items §4 uses; HRS core items 2016–2024; the 2016 employer-sponsored pension-wealth product. First, the four checks in §2 and the item verification of §4.1. Label-verified at read time against the codebooks; releases only through §3's interface; failures as fixed-schema diagnostics; the `integration_hrs` tier; the separate account if Max chooses it | Exact labels at read time; refusal when `POPULACE_DYNAMICS_HRS_DIR` is unset or a file is unstaged; the release-boundary, diagnostic and isolation tests in §7 | 5–8 / 1.25–2 (4–6.5 / 1–1.625 without the separate account) | Public HRS files in place | IR0's HRS entries; SSI0's HRS column; WP5; WP8; SSI5 (B) or SSI4 (A) |

### 5.2 Changed rows in design §4.1

| Id | Change | Depends on (added) | Estimate change |
|---|---|---|---|
| IR0 | HRS entries in WP-G's and SSI-G's records: held-out waves by item reference period; weights and design variables; WP-G's HRS estimand, observation operator and standardization procedure; HRS cell families, the joint role partition (option A) and their power audit; the HRS release policy and publication minimum; the U2 extension (§3). IR0's other records do not wait for them | D6, for the HRS entries only | +1.5–2.5 d |
| SSI0 | Contract `ssi0-v2` with an HRS column for all 53 rows, in a later PR than #573 | D6's verified item list | +1–2 d |
| SSI4 | Option A only: HRS joins the training partition | D6 (A) | +2–3 d (A) |
| WP5 | HRS cell families, registered separately, with their within-HRS floor (§4.1) | D6 | +1–2 d |
| SSI5 | Option B only: HRS cells as a third held-out population; floor and null | D6 (B) | +2–3 d (B) |
| SSI5R | Option B only: the one-shot candidate run includes the HRS cells | — | +0.5–1 d (B) |
| WP8 | HRS added to the report-only checks | D6 | +0.5–1 d |

### 5.3 Changed rows in design §4.2

| Id | Verification class | Admitted scope on success | Ledger row |
|---|---|---|---|
| D6 | Accounting conformance | Readers for the listed products, years and items only | None directly |
| WP5/WP6 | Unchanged | Adds the HRS cells WP-G registers and passes, ages 51 and over, by birth cohort, age band and sex, reported apart from the PSID cells | Wealth: adds a second held-out population for the cells IR0 powers |
| SSI5R (B) | Unchanged | Adds aged annual-state receipt propensity on the registered HRS cells | SSI: a third held-out survey for aged receipt; SSA caseload validation by age stays open |

### 5.4 Design §5: the excluded row splits

The design's row "Excluded: HRS and RAND HRS (2024 core early release); HRS–SSA restricted earnings, benefits and SSI records…" becomes two rows:

| Gate or use | Source | Role | Access | Lead time | Staged |
|---|---|---|---|---|---|
| WP-G, WP8; SSI-G (B) or SSI4 (A) | HRS public files: RAND HRS longitudinal file (final 1992–2020, early 2022) and detailed imputations (2002–2020); HRS core 2016–2024; the 2016 employer-sponsored pension-wealth product (catalog §§7–8) | HRS cell families in WP-G at ages 51 and over, admitted with a registered standardization; report-only for WP8; third held-out population for SSI-G (B) or SSI4 training (A) | Public HRS files under the project's data-access record | Registration turnaround unverified | No (D6) |
| Excluded | HRS–SSA restricted earnings, benefits and SSI records (SSI January 1974–December 2024; catalog §9) | Not used; could supply administrative earnings for eligible linked respondents. Effects on lifetime-group assignment and SSI reporting accuracy remain unverified | Restricted access | Application decisions typically 6–8 weeks; end-to-end onboarding unverified | No; unpriced (design §11) |

### 5.5 Other sections

- **Design §5's opening sentence.** "SIPP, SCF and HRS microdata are not staged" stays true until D6.
- **Design §9.** Adds D6's invariants (§7 below).
- **Design §10.2.** Adds a named condition:

  | Condition | Trigger | Stops |
  |---|---|---|
  | `HRS_SOURCE_UNAVAILABLE` | The public HRS files are not in place, or HRS revises its access or use requirements, or the project's data-access record no longer covers a use | Stop the affected HRS use and every admission or computation that requires it. Publish an unavailability or abort record. Other work continues only within its independent registered scope. Register any fallback or reduced-scope gate before candidate outcomes; retain failed or unsupported cells and their exposure, and never claim a pass by removing them |

- **Design §11.** The excluded item "HRS and SSA-linked restricted data, their access time and loaders" becomes "the HRS–SSA restricted products, their access time and loaders". HRS registration turnaround is also excluded.
- **Design §12.** Item 7 is unchanged. A new item asks Max whether to approve this addendum, which SSI option, and whether to set up the separate account (§9).

## 6. Price

### 6.1 Rows

Each range is an engineering judgment, on the design's unit of one reviewed engineer-day (design §11).

| Item | Work | Estimate |
|---|---|---|
| D6 | The four checks in §2 (0.5–1); readers for four products on the codebook layouts (2–3); the release interface and diagnostic schema, and their synthetic-fixture tests (1–2); the separate-account worker and its isolation test, if Max chooses it (1–1.5); the `integration_hrs` tier and its `tests/tier_counts.json` change, which waits for the coordinator's tier-count slot (0.5) | 5–8 d |
| IR0 | Item reference periods and held-out waves (0.25–0.5); weights and design variables (0.25–0.5); WP-G's HRS estimand, observation operator and standardization procedure (0.5); cell families and power audit for two gates (0.5–0.75); release policy, publication minimum and U2 entry (0–0.25) | 1.5–2.5 d |
| SSI0 | 53 HRS decisions from D6's item list, their tests, and contract regeneration | 1–2 d |
| WP5 | HRS cells in the registration package, with the registered standardization (0.5); the within-HRS floor (0.25–1); scoring and reporting, with the PSID–HRS discrepancy reported separately (0.25–0.5) | 1–2 d |
| WP8 | HRS's report-only tables beside the other checks | 0.5–1 d |
| SSI4 (A) | Harmonization (1–1.5); training partition and refit (1–1.5) | 2–3 d |
| SSI5 (B) | HRS cells in the registration package (0.5–1); after registration, floor (0.5–1); null scored before the candidate (1) | 2–3 d |
| SSI5R (B) | SSI5R alone scores SSI4's model once on the HRS cells, and publishes | 0.5–1 d |

**Totals,** with the separate account. Without it, subtract 1–1.5 d from D6 and from every total below except tier 2's.

| | Option A | Option B |
|---|---|---|
| Tier 1 | D6, IR0, SSI0, WP5, SSI4: 10.5–17.5 d | D6, IR0, SSI0, WP5, SSI5, SSI5R: 11–18.5 d |
| Tier 2 | WP8: 0.5–1 d | WP8: 0.5–1 d |
| **Addendum** | **11–18.5 d** | **11.5–19.5 d** |
| Tier 1 with the design's 123–186 d | 133.5–203.5 d | 134–204.5 d |
| **Base with the design's 182–278 d** | **193–296.5 d** | **193.5–297.5 d** |

### 6.2 Lanes and critical path

The design's lane schedule (design §4.3) changes as follows, in engineer-day equivalents from the start. D6's separate account changes no date below, because D6 is not on the critical path either way.

- **WP lane.** D6 runs after WP2, in the slack before D1 ends: WP2 ends at 4–6, D6 at 9–14, and D1 at 10–14, so WP1 still starts when D1 ends. WP5 grows to 10–15 d and ends at 40–59; WP6 ends at **43–64 d** (from 42–62). IR0 still does not bind WP5: WP4 ends at 30–44, after IR0.
- **Data-and-audit lane.** IR0 grows to 7.5–11.5 d and ends at **26.5–40.5 d** (from 25–38). Its HRS entries need D6, which ends earlier, at 9–14. D3, which follows IR0, ends at 29.5–44.5.
- **CE lane.** CE4 waits for IR0 and ends at 32.5–49.5; CE5 ends at **34.5–52.5 d** (from 33–50).
- **SSI lane, option B.** SSI0's HRS column needs D6's item list, so it runs after D6, in the lane's wait for D4: SSI0 and SSI1 end at 8–12 as before, the HRS column starts when both they and D6 are done (9–14) and ends at 10–16, and D4 ends at 14–21, so SSI2 still ends at 20–30. SSI4 waits for IR0 and ends at 34.5–52.5; SSI5 grows to 8–12 d and ends at 42.5–64.5; SSI5R grows to 2.5–4 d and ends at **45–68.5 d** (from 41–62).
- **SSI lane, option A.** SSI4 grows to 10–15 d and ends at 36.5–55.5; SSI5 ends at 42.5–64.5; SSI5R ends at **44.5–67.5 d**.

**If the public files are late.** These dates assume the public files are in place when WP2 ends. If they arrive later, the coordinator reschedules D6 within the four serial lanes and publishes revised dates before HRS work enters a gate. IR0's HRS entries may follow as a supplement, but D6 can delay WP1 and the PSID work after it if it consumes the slack before D1 ends (on time, 0–1 d); the HRS contract update can also delay SSI2 if it finishes after D4. The original cells avoid those delays only if the HRS work fits around their predecessors, or if HRS is deferred to a later registered attempt.

So all three tier-1 gates' first attempts publish after about **45–68.5 engineer-day equivalents (11.3–17.1 lane-weeks) under option B**, or 44.5–67.5 (11.1–16.9) under option A, against the design's 42–62. The SSI lane stays the last to finish.

**Second attempts.** Each retry rebuilds its floor (design §4.3), and the floor now includes HRS cells: add 0.5–1 d to a WP-G retry, and, under option B, 0.5–1 d to an SSI-G retry. Under option A, an SSI-G retry refits SSI4 with HRS (no added days beyond the refit already priced).

## 7. D6's invariants and tests

Each is stated in D6's PR and tested with property-based tests (Hypothesis) beside example tests, on synthetic fixtures unless marked `integration_hrs`.

- **Release boundary.** Metadata and row-count responses are tested separately from cell statistics. On synthetic fixtures, cell statistics below the release policy's distinct-contributor minimum refuse or suppress; row-returning operations refuse; prohibited overlapping releases refuse; and no minimum or maximum is released. Confidentiality is not tested by comparing aggregate values with individual input values.
- **Errors.** Synthetic tests place unique sentinel tokens in malformed record fields (bad types, truncated lines, unknown codes) and check that no released diagnostic contains those tokens and that every diagnostic validates against the fixed schema.
- **Isolation, with the separate account.** On the worker host, synthetic probes get the same ownership and permissions as the worker's data, temporary and raw-output files. The worker can read them. From the actual agent execution identity and its tools, attempts to read known probe files must fail specifically with permission denial; directory-type and missing-path errors do not pass. A unique sentinel in the worker's environment must not be exposed to that identity by the host's process-inspection interfaces. These checks run when Max selects the separate-account setup; otherwise D6 records that isolation is not configured.
- **Refusal.** The worker refuses when `POPULACE_DYNAMICS_HRS_DIR` is unset, the directory is inside the repository or a git worktree, or a file is unstaged or fails its label check.
- **Labels.** Each item read matches its codebook label exactly; a mismatched or missing label refuses that item.
- **Weights.** A statistic that needs weights refuses when they are missing, never falls back to unweighted values, and is invariant to row order.
- **Small cells.** Any table marked for publication suppresses cells below IR0's publication minimum, and the suppression is reported, never silent.
- **Tier.** A test module that names `POPULACE_DYNAMICS_HRS_DIR` is classified `integration_hrs`, and its tests are skipped when the variable is unset.

## 8. Risks and stop conditions

| Risk | Consequence |
|---|---|
| The public files have no separate SSI receipt item (§2, item 1) | Both SSI options drop; SSI0's HRS column is not built; the addendum's price falls by 3.5–6 d (B) or 3–5 d (A) |
| The public files lack valid survey-design uncertainty inputs (§2, item 2) | HRS cells are not admitted to WP-G or SSI-G. A descriptive HRS table is released only if its inputs and release independently satisfy the registered rules, and WP5's and SSI5's HRS work shrinks to that reporting |
| No HRS wave's items fall wholly after 2013 (§2, item 4) | HRS cells in WP-G are retrospective regression evidence only, not held-out prediction |
| IR0 cannot register a common estimand, observation operator and standardization for WP-G's HRS cells (§4.1) | WP-G's HRS cells stay report-only; its PSID cells are unaffected |
| A required item, label, ownership crosswalk or uncertainty input cannot be verified | Refuse the affected item or case and retain its status and denominator. Block admissions that require it. Release a descriptive statistic only if its inputs and release independently satisfy the registered rules |
| The 1946–55 cohorts' HRS cells collide with U2's sequencing (§3) | Those cells wait for U2's posted result, or are listed in `RESTRICTED-FILES.md` first |
| `HRS_SOURCE_UNAVAILABLE` (§5.5) | Apply §5.5's dependency and fallback rules; work with an independent registered scope continues |
| The separate account is not set up | D6 costs 1–1.5 d less, and the boundary rests on the rules, the release interface and the tests, without enforced isolation (§3) |

## 9. Decision for Max

**Approve this addendum, which SSI option, and whether to set up the separate account?** Recommended: approve with option B and D6 in tier 1, and set up the separate operating-system account for D6's worker. Option B stands as a gate only if IR0 finds a powered, harmonized HRS cell for SSI-G; otherwise its HRS SSI cells are report-only and option A stays available as a new registered version (§4.4). The alternatives are option A, or deferring HRS to tier 2, which leaves the design unchanged now. Either way, design §12 item 7 on the restricted products stays a separate question.

## 10. Sources read

- The design, `docs/design/income_and_resources.md`, as merged: §§2.7, 3.2, 3.3, 4.1–4.3, 5, 7.1–7.3, 9, 10.2, 11 and 12.
- The lane's source catalog, `EV/income-resources-20261021/research/data-sources.md`, §§7–9.
- `src/populace_dynamics/income_resources/ssi/input_contract.json` and `docs/analysis/ssi0/source_contract.md` on PR #573's branch (`ssi0-v1`; 41 engine and 12 context rows; populations PSID, SIPP and Microcosm).
- `tests/conftest.py` on master (the tier markers and the PSID source indicators), `tests/tier_counts.json`, `.github/workflows/tests.yml` (no marker filter) and `tests/data/test_family_income_integration.py` (its `skipif` marker).
- `docs/adr/0002-uk-extension-ukhls.md` on master (status proposed; the n ≥ 10 cell-suppression convention).
- No HRS data file, codebook or product page was opened for this addendum; every HRS fact comes from the catalog.
