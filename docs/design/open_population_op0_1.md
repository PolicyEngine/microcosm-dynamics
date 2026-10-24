# Open population OP0.1 source, exposure, access and power audit

**Status: draft records, not frozen; held-out years pending the shared registry and Track B’s J. A blinded feasibility and power review comes before any registration. Registrations go to issue #42 only through the coordinator on Max’s go.**

Audit date: 2026-10-24. This is a documentation and exposure audit, not a population estimate, power result or gate registration. It reads no microdata and computes no real-data statistic. Proposed choices and unestablished inputs block freeze; they do not become defaults by appearing here. PSID use follows the project's data-access record.

## Authority and registry boundary

The approved revision-12 design is `5c82dbd9:docs/design/open_population.md`, SHA-256 `964356ad282e86bc1b128b93ec226b38fc3bb9bd6fe8a84162179bd608600154`; its §10 records Max’s revision-11 approval and ruling d1922. Its §3.1, §3.2, §4 and §5.2–§5.4 define these records. Track B design revision 3, §5.1–§5.2 and §7, supplies the audit and power protocol (read 2026-10-24).

The permitted registry snapshot is `daf02425:docs/design/track_b_holdout_registry.json`, SHA-256 `084b8d50ba3c0fe7cf9bd70e3c7c700c60ae682644ead99cca2bb116bfb2ef88`. Its mutation evidence is `daf02425:docs/design/track_b_holdout_registry_mutations.json`, SHA-256 `0be8a0c8be8eb7d014587d7bbb58a2b980374a334ccaedf5cd0e25d588fbfa1f`. These are draft PR #560 bytes, not a merged snapshot.

Only H001–H005 historical uses appear; J has no candidate entry and `complete` is false. The source vocabulary has no ACS PUMS, NCHS natality, Census count/estimate/projection, OACT demographic or CBO projection source yet. Absence does not clear a year. The coordinator must add reviewed source/family definitions, reserve J first, review underlying-data overlaps, append OP candidate entries before freeze, and cite the merged registry by commit and byte hash. Scopes never narrow same-source overlapping years; unresolved relations need symmetric named disclosure; disjoint same-family relations need substantive citations (`daf02425:src/populace_dynamics/track_b/holdout_registry.py:8–44,76–159,396–410,756–804,1033–1078,1105–1171`). This lane edits neither the registry nor Track B code.

## Reading the records

The JSON companion is authoritative for field completeness; this audit states the same drafts for review. `available` means documentation establishes a source/variable, not that data bytes were accessed or a target approved. `validation_only` excludes selection. `not_available` means the requested margin was not established in the inspected release. Every uncaptured target byte hash remains `to capture`. A source’s reachable documentation does not confirm its data file: those checks remain unverified under this lane’s no-data rule.

The common statistical proposal is a simultaneous 95 percent bound with Bonferroni over a frozen cell family, Monte Carlo error below one-tenth of each tolerance, and an inconclusive result for inadequate precision. Survey tolerances use the source design; vital/administrative aggregates use measurement/concept/coverage/vintage allowances; census counts use matching published coverage measurement. No real-data power or tolerance was calculated. The named power procedures below require prospective blinded review and a 0.90 operating-characteristic requirement; effect sizes, cell families and pooling ladders remain proposals until that review.

<!-- records:start -->

## Birth record (OP2)

**`gate_birth` — draft.** Verification: retrospective regression default. Unaligned births by maternal five-year age group and share male in OP5's roster, conditional on OP3/OP4 flows. Independent prediction only for separately demonstrated unused observations/estimands.

### Sources, variables and population

- nchs: Final NVSS natality 2015 candidate, with 2016–2019 and 2023–2024 exposed regression companions; exact table/extract vintage to pin.
- acs: 2013 1-year PUMS start; 2010–2013 immigrant donor files.
- cps_fertility: CPS June 2012 recommended parity-fit candidate preceding 2013 start; June 2014 documented alternative, not selected. Max/coordinator chooses release.

- Resident births; mother's five-year age; infant sex; mother's nativity; MAGER single age and MBSTATE_REC/SEX/IMP_SEX as candidate codebook fields.
- Exposed NCHS ASFRs and female resident exposure denominators; projected persistent parity and sex draw.
- Married-mother share remains report-only until B4 forward marriages.
- Proposed CPS 2012 PESF1 children-ever-born, PXSF1 allocation flag, PWSSWGT basic-CPS weight; female fertility-question ages 15–50. Missing/not-in-universe never zero.

Population: Resident births to women in the declared fertile-age support, projected from OP5. Endpoint age coverage must match the reference; no silent substitution of births to all U.S. occurrences for U.S. resident births.

Universe bridge:

- NVSS resident birth numerator and resident female denominator must use the same geography and age universe as OP5, including a declared group-quarters contribution.
- NCHS MBSTATE_REC treats U.S. possessions differently from ACS native/foreign-born and does not establish citizenship of parents abroad; nativity comparisons require a frozen bridge.
- PSID use follows the project's data-access record.
- CPS June 2012 covers civilian noninstitutional household women 15–50; OP5 includes GQ and other ages. A parity mapping/out-of-domain rule is required outside that CPS support.

Date mapping:

- NVSS events refer to calendar year Y; collect OP1's birth-event journal within Y, rather than inferring births from the next stock.
- Use OP5's proposed July 1 2013 start with a declared first partial-year exposure bridge; annual-slice ages must be bridged to mother's age at delivery.
- Pin birth-year sex-ratio estimation data separately: a year used to set that ratio cannot also validate share male independently.
- CPS June 2012 interviews June 17–23; children-ever-born measured then must be bridged to July 1, 2013 proposal without treating interval births as observed. 2014 cannot be a 2013-vintage fit without explicit disclosure.

### Exposure and partition

- NCHS 2016–2024 five-year ASFR annual series consumed by scripts/build_gate2_floors.py:626-674,693-743; ratios declared REPORTED, not tuned, not proof of no subsequent selection.
- TR2026 default explicitly selects NCHS 2024 interpolated shape: src/populace_dynamics/baselines/asfr.py:67-126; baselines/tr2026_intermediate.py:84,165-168. This is selected baseline structure.
- 2015 outside producer range; infant sex, maternal nativity and observed single-age natality are outside its all-race five-year ASFR extraction. Their nonuse remains bounded to the audited repository; off-repository/other-lane disclosure remains open.
- See exposure inventory for transitive consumers and audit exceptions.

| Source | Tentative year | Status | Reason |
| --- | --- | --- | --- |
| nchs | 2015 | pending_registry | Candidate only: outside committed annual ASFR range. Do not read until source/estimand exposure, J and registry review clear it. |

Fit years:

- Fertility kernel's documented fit support, parity seed source and sex-ratio vintage to pin; no candidate seed chosen from a scored birth estimand.

Overlaps:

- with: gate_pop; years: [2015]; reason: Its 2013→2020 path contains births in this year; disclose shared demographic trajectory and natality source use. Different outcome sources do not prove independence.
- with: Track B J; years: []; reason: No J candidates recorded; coordinator must check underlying data/family relation.

Registry rule: J first; no year is cleared by absence from this incomplete registry.

Excluded years:

- years: 2016–2024; reason: Age-group ASFRs exposed; regression only.
- years: 2020–2022; reason: Shock-window diagnostics, not admission cells.

Registry: `daf02425:docs/design/track_b_holdout_registry.json`, SHA-256 `084b8d50ba3c0fe7cf9bd70e3c7c700c60ae682644ead99cca2bb116bfb2ef88`; J candidates absent; recheck merged commit/hash before freeze.

### Cells, tolerance and uncertainty

| Cell | Estimand | Eligibility |
| --- | --- | --- |
| maternal_age_asfr | Resident births per exposed woman-year in seven gate-2 five-year maternal-age bands, with endpoint bridge explicitly fixed. | Reference metadata, support and precision rules fixed before outcomes. |
| share_male | Male births / births with declared treatment of unknown/imputed sex. | Sex-ratio pin must use disjoint observations/estimand; otherwise regression. |

| Reference | Tolerance class | Prospective procedure |
| --- | --- | --- |
| nchs | administrative_and_vital_statistics_aggregates | No manufactured sampling floor. Before lock, pin an allowance for same-target-year revision/vintage dispersion, measurement/concept/coverage bridges and half the published rounding unit. Variation between outcome years is not measurement uncertainty. Numeric allowance remains unset; this blocks freeze. |
| acs | survey_microdata | Proposal from design §5.3: \|ln(candidate/reference)\|; survey-design replicates where available, otherwise household-disjoint half-splits; round(mean + 4*sd, 3), at least 20 events on the weaker half, stabilized tolerance <= ln(1.5). A fixed prospective pooling ladder partitions ineligible cells as report-only. Zero references require a separately registered absolute-scale rule. |
| popest | administrative_aggregate_denominator | No manufactured sampling floor. Before lock, pin an allowance for same-target-year revision/vintage dispersion, measurement/concept/coverage bridges and half the published rounding unit. Variation between outcome years is not measurement uncertainty. Numeric allowance remains unset; this blocks freeze. |
| cps_fertility | survey_microdata | Survey microdata for parity-fit uncertainty: June 2012 uses PWSSWGT, no separate supplement weight. Attachment 16 generalized variance methods documented; public replicates unestablished. Recommend approved household-disjoint split/cluster procedure with allocation and June-to-start bridge uncertainty; do not manufacture a design. |

All numeric allowances remain proposals requiring blinded review. Simultaneous 95% confidence bounds with Bonferroni over the frozen cell family; include reference, estimation, design and simulation uncertainty. Monte Carlo standard error below one-tenth of each tolerance. Insufficient precision is inconclusive. Never drop a failed/unsupported cell after outcomes.

Candidate uncertainty: Resample OP5 housing units by the ACS design and GQ persons separately; resample OP3 donors under their own replicate designs; refit/perturb parity seeds and the fertility law within documented estimation support; propagate mortality/exit and timing bridge uncertainty; repeat person-keyed simulation seeds. Preserve mother/child and family clustering. OP5 resampling applies because this gate projects from OP5.

Pass conjunction:

- All frozen eligible maternal-age and share-male simultaneous bounds inside source-class tolerances; all support/MC conditions met.
- No known exposure is called independent prediction. Regression failure blocks its corresponding admission; no seed or tolerance selection.
- Named newborn-link and persistent-parity conformance prerequisites pass separately; married-mother share is report-only.

### Power procedure

**Nested clustered equivalence and misspecification simulation for birth cells.** Status: `not_run_no_real_data`. Proposal: require >=0.90 full-conjunction admission probability under prospectively named in-margin scenarios (including exact agreement and reviewer-chosen near-margin profiles), with a simulation interval precise enough for the review. Effect sizes, tolerances and cell family must be frozen before outcomes. Separately estimate false-admission probability for prespecified out-of-margin profiles; no admission or inconclusive alone is not evidence the procedure detects a wrong mechanism. No power demonstrated.

For frozen empirical cells j with discrepancy d_j=|ln(C_j/R_j)| and prospective tolerance delta_j: H0 is at least one d_j >= delta_j; H1 is all d_j < delta_j. A separately registered absolute discrepancy replaces log ratio for zero cells. Full-conjunction admission power is P(all simultaneous intervals inside their margins) under a named in-margin alternative, not probability of inconclusive.

Required inputs:

- Pinned critical-cell event/exposure sizes or blinded authorized counts; same-year vintage/rounding allowances; design effects and covariance; fitted-law/parity uncertainty; OP5/OP3 clustering; simulation seed variance.

Procedure:

- Run an invented-data effective-size/design-effect grid; perturb one age/sex profile at a time and jointly; refit only development data.
- Nest survey/fitted-law resampling and repeated projection seeds, form Bonferroni simultaneous bounds, estimate the full-conjunction probability and binomial Monte Carlo interval.
- Freeze required effective sizes, alternatives and pooling ladder prospectively; absence of matched counts or >=0.90 support blocks feasibility approval.

### Targets and fitted support

| Entry/source | Table | Row | Column | Vintage | Byte hash | Status/role |
| --- | --- | --- | --- | --- | --- | --- |
| birth_age / nchs | NVSS final natality annual age-rate release; exact table to capture | Maternal five-year ages, endpoints to reconcile | Births and resident-female ASFR denominators | 2015 candidate / exposed 2016–2024 | to capture | available / reference |
| birth_sex / nchs | NVSS natality codebook SEX/IMP_SEX; aggregate output to capture | Male, female, unknown/imputed | Resident birth counts | 2015 candidate | to capture | available / reference |
| birth_nativity_single_age / nchs | MAGER and MBSTATE_REC codebook; output not selected | Observed maternal single age / mother's birthplace | Birth counts; matching denominators not established | 2015 candidate | to capture | validation_only / reference |

| Component | Fitted or captured support | Rule outside support — proposal unless stated |
| --- | --- | --- |
| fertility | Candidate16 female person-years; ages 15–49, parity categories0,1,2,3 with 3 meaning3+; probabilities keyed by(age,min(parity,3),birth decade). Training uses age-kernel bandwidth3 and only represented cohort/parity exposure. Committed seed metadata lists decades1880–2000 by 10 for seeds 0,1,2,4 and 1890–2000 for seed 3; no2010+ cohort. | Historical component initializes absent cells to zero, clips age indices/caps parity and returns zero for unknown cohort. This is existing behavior, not a ratified extrapolation rule for OP2. Recommend refuse unsupported cohort/stratum until Max ratifies a labeled terminal-cohort or other continuation; do not silently claim post 2030 fertility support. |
| parity_seed | CPS June 2012 PESF1 among household women 15–50 is a documented proposal, with allocation flag PXSF1 and basic PWSSWGT. Own-children proxy alternative differs from children ever born. | Unknown/not-in-universe preserved; explicit GQ/age/date bridge or named refusal. Release/seed mapping remains for Max. |

Access: `nchs`, `acs`, `popest`, `cps_fertility` in the access table below. Each record carries the full source access fields in JSON; all data-file checks remain unverified.

### Proposals and open questions

- Retain age-ASFR regression arm; reserve 2015 and independently unused sex/nativity/single-age observations only after external exposure confirmation.
- Recommend CPS June 2012 children-ever-born for a pre 2013 parity seed; ratify release, age/GQ/date bridge, allocation and variance procedure before use.

- Which observations pin sex ratio without consuming the share-male validation target?
- Can the coordinator demonstrate nonuse outside the repository of 2015, sex, nativity and observed single-age outcomes?
- What numeric coverage/concept/vintage allowances and zero-cell rule does Max approve?

Evidence for this record:

- 5c82dbd9:docs/design/open_population.md:291-363
- scripts/fetch_nchs_asfr.py:52-62,257-293,309-360
- scripts/build_gate2_floors.py:626-674,693-743,924-931
- src/populace_dynamics/baselines/asfr.py:67-135
- src/populace_dynamics/baselines/tr2026_intermediate.py:84,165-168
- https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Dataset_Documentation/DVS/natality/UserGuide2015.pdf pp.5-6,27
- src/populace_dynamics/models/family_transitions/components/fertility.py:28-45,80-94,123-157,170-194
- src/populace_dynamics/engine/marital.py:352-374
- runs/gate2_hazard_v16.json:8732-8759,12485-12512,16238-16265,19990-20017,23742-23769 (age/parity/cohort metadata only)
- https://www2.census.gov/programs-surveys/cps/techdocs/cpsjun12.pdf Attachments3,7,8,16
- https://www2.census.gov/programs-surveys/cps/techdocs/cpsjun14.pdf Attachment7
- gates.yaml:1298
- docs/baselines.md:555-557
- src/populace_dynamics/baselines/cbo2026_long_term.py:330
- src/populace_dynamics/baselines/tr2026_intermediate.py:245
- src/populace_dynamics/baselines/fertility.py:169-174
- src/populace_dynamics/baselines/track_a.py:286-287
- src/populace_dynamics/baselines/__init__.py:72-76

## Immigration record (OP3)

**`gate_imm` — draft.** Verification: held out stock proxy prediction and bridge conformance. Recent-arrival demographic composition conditional on gross inflow; admits a surviving/staying stock proxy, not true entry-time state, legal status, gross flows or later earnings.

### Sources, variables and population

- acs: Separately weighted 2010, 2011, 2012, 2013 annual 1-year PUMS fit; 2014 annual 1-year PUMS candidate score. Person, housing-unit and replicate weights; never five-year pooled files.
- oact: TR2026 intermediate V.A2 gross positive LPR plus temporary-or-unlawfully-present inflow; exact captured table version pending.

- AGEP,SEX,NATIVITY,CIT,POBP,YOEP; MAR and RELP (2010–2014), SERIALNO,SPORDER,SFN,SFR,NP,TYPE; disability items and a declared parity imputation.
- PWGTP/PWGTP1–80 and WGTP/WGTP1–80; entry packet may later need SCHL,ESR,WAGP,SEMP,PINCP,ADJINC for OP8 (not OP3 economic admission).
- V.A2 inflow components separate from outflow, adjustments of status and net change; no donor legal-status label.

Population: Foreign-born recent-arrival stock in each annual ACS release, proposed YOEP in collection year or immediately preceding year, with unknown/not-applicable codes explicitly partitioned. Exact recent-arrival window is a coordinator question; no microdata inspected.

Universe bridge:

- ACS resident housing-unit/GQ population differs from Social Security area. CY catalog includes territories, personnel/dependents abroad and other abroad groups. Recommend an explicitly documented resident-component mapping or named refusal; no numeric share assumed.
- Use NATIVITY plus CIT/POBP and YOEP, not YOEP alone; donor interviews observe stayers/survivors and current households, not original arrival parties.
- Arrival units are observed household/subfamily packets with declared unknown links; the relationship-to-reference-person item determines only some spouse/parent links. An intact original migration party is an assumption, not observed.

Date mapping:

- ACS responses collected Jan 1–Dec 31, with ages/states at response, are not a July 1 snapshot. Fit each annual file with its own weights; score the separately weighted 2014 stock after lock.
- Existing seam appends entries before mortality then aging; entrant for Y carries year=Y-1 and entry_age. Temporary-or-unlawfully-present control counts year-end stayers. OP3 must bridge each component to its seam exposure without filtering survival twice (engine/entrant_schedule.py:14-22,359-371).
- Propose deaths first and emigration among survivors in the mortality slot. Same-year entrant exits are component-specific and remain open with OP4. Freeze the exposure fraction/entry-age mapping before constructing real schedules.

### Exposure and partition

- No ACS PUMS reader or data-read invocation established in searched src/scripts/tests; gate2b/2c blocks describe ACS aggregate anchors, not PUMS readers (inventory). This is bounded repository evidence, not proof a person never read ACS elsewhere.
- U2 source registry is documentary only; PSID weight documentation describes upstream ACS 2015, 2017, 2019 calibration. Disclose indirect calibration exposure; do not call those ACS years pristine.
- 2010–2013 will be fitting exposure; 2014 remains unread by this audit. Catalog/dictionary reads do not inspect survey outcomes.
- Conditional upstream exposure: if OP3 timing/exposure bridge consumes OP4 Census 2023 exit assumptions, their ACS 2011–2015 upstream fit includes2014. Independent2014 admission remains unresolved unless the bridge uses an admissibly disjoint assumption source or a reviewed narrower claim. The annual PUMS file staying unread here does not remove that dependency.
- Prior use is reported, not merely proposed: docs/progress.md:331 and docs/progress/progress.json:115 record a 2026-09-06 report-only entrant schedule, a captured/hash-pinned Trustees immigration table and certified-frame donor feasibility check. Current missing native readers do not establish historical nonuse; exact source cells/controls in that older run remain uninspected here.
- Microcosm frame documentation names ACS as an upstream source without identifying years/estimands (docs/infrastructure.md:104-106; docs/methodology.md:9-11; docs/funder-summary.md:174-175). Frame-based prior uses cannot clear ACS 2010–2019 without upstream provenance, even if this checkout has no PUMS reader.

| Source | Tentative year | Status | Reason |
| --- | --- | --- | --- |
| acs | 2014 | pending_registry | Approved-design annual recent-arrival stock holdout; tentative until repository/external disclosures and merged registry clear it. |

Fit years:

- 2010
- 2011
- 2012
- 2013

Overlaps:

- with: OP5 / gate_pop / gate_birth; years: [2013]; reason: OP3 training donors share ACS 2013 with OP5 start; candidate uncertainty must couple shared construction rather than assume independent samples.
- with: Track B J; years: []; reason: No J candidates; do not reserve before J.
- with: OP4 Census 2023 emigration assumptions; years: [2014]; reason: Census methodology combines rates based on ACS 2011–2015, including 2014. If those rates enter entry survival/exposure adjustment, disclose upstream holdout overlap; coordinator must resolve independent status before freeze.

Registry rule: J first; no year cleared by absence from incomplete registry.

Excluded sources:

- ACS five-year pooled files

Selection rule: No 2014 read for fit, pooling, tuning, packet choice or floors before lock.

Registry: `daf02425:docs/design/track_b_holdout_registry.json`, SHA-256 `084b8d50ba3c0fe7cf9bd70e3c7c700c60ae682644ead99cca2bb116bfb2ef88`; J candidates absent; recheck merged commit/hash before freeze.

### Cells, tolerance and uncertainty

| Cell | Estimand | Eligibility |
| --- | --- | --- |
| margins | Recent-arrival age-band, sex, nativity/citizenship and years-since-entry shares. | Frozen event/support and effective-size rules; no legal-status inference. |
| joints | Proposed age×sex, age×entry-duration, marital/arrival-unit-type×sex joints; exact family and pooling ladder for blinded review. | Support >=20 weaker-half events where half-splits apply; replicate-design precision and T_max criterion. |

| Reference | Tolerance class | Prospective procedure |
| --- | --- | --- |
| acs | survey_microdata | Proposal from design §5.3: \|ln(candidate/reference)\|; survey-design replicates where available, otherwise household-disjoint half-splits; round(mean + 4*sd, 3), at least 20 events on the weaker half, stabilized tolerance <= ln(1.5). A fixed prospective pooling ladder partitions ineligible cells as report-only. Zero references require a separately registered absolute-scale rule. |
| oact | administrative_aggregate_control | No manufactured sampling floor. Before lock, pin an allowance for same-target-year revision/vintage dispersion, measurement/concept/coverage bridges and half the published rounding unit. Variation between outcome years is not measurement uncertainty. Numeric allowance remains unset; this blocks freeze. Control matching is conformance, not independent validation. |

All numeric allowances remain proposals requiring blinded review. Simultaneous 95% confidence bounds with Bonferroni over the frozen cell family; include reference, estimation, design and simulation uncertainty. Monte Carlo standard error below one-tenth of each tolerance. Insufficient precision is inconclusive. Never drop a failed/unsupported cell after outcomes.

Candidate uncertainty: Resample OP3 donor files by each year's replicate design and household/family packets (GQ person units separate), refit the donor-composition/packet law on 2010–2013 only, propagate any fit and universe/timing-bridge uncertainty, then repeat schedule/projection seeds as needed. Do not substitute OP5-start resampling for this donor uncertainty. Couple reference and candidate shared inputs explicitly.

Pass conjunction:

- Every eligible registered marginal/joint simultaneous bound inside survey tolerance and MC target met.
- Universe and component-specific timing/exposure bridges pass invented-data conformance, including a deliberately duplicated survival filter that must fail.
- Keep all unsupported/ineligible cells report-only under a frozen machine partition; DONOR_SUPPORT_THIN or unresolved bridge blocks the corresponding admission.

### Power procedure

**Replicate-design donor refit simulation for the full immigrant-stock conjunction.** Status: `not_run_no_real_data`. Proposal: require >=0.90 full-conjunction admission probability under prospectively named in-margin scenarios (including exact agreement and reviewer-chosen near-margin profiles), with a simulation interval precise enough for the review. Effect sizes, tolerances and cell family must be frozen before outcomes. Separately estimate false-admission probability for prespecified out-of-margin profiles; no admission or inconclusive alone is not evidence the procedure detects a wrong mechanism. No power demonstrated.

For frozen empirical cells j with discrepancy d_j=|ln(C_j/R_j)| and prospective tolerance delta_j: H0 is at least one d_j >= delta_j; H1 is all d_j < delta_j. A separately registered absolute discrepancy replaces log ratio for zero cells. Full-conjunction admission power is P(all simultaneous intervals inside their margins) under a named in-margin alternative, not probability of inconclusive.

Required inputs:

- Annual PUMS recent-arrival sample/effective sizes by critical cell, weights/design covariance, household/GQ clustering and unknown-code rates.
- Published overall ACS sizes are insufficient; recent-arrival cell sizes were not located in documentation. Authorized blinded counts or matched published documentation required.
- Proposed cell family/pooling ladder, design-effect grid, fitted-law estimation and control/timing-bridge sensitivities.

Procedure:

- Simulate invented household/GQ donor packets across effective-size/design-effect grid; fit only 2010–2013 construction.
- Apply full/80 replicate weighting and donor refits; hold 2014 scoring construction disjoint; calculate simultaneous intervals and full-conjunction operating characteristics.
- Blinded reviewer chooses smallest admissible scope with >=0.90 power before any candidate result; otherwise inconclusive / DONOR_SUPPORT_THIN.

### Targets and fitted support

| Entry/source | Table | Row | Column | Vintage | Byte hash | Status/role |
| --- | --- | --- | --- | --- | --- | --- |
| imm_lpr / oact | TR2026 V.A2 | Calendar year Y | LPR inflow (not net change or status adjustment) | 2026 | to capture | available / control |
| imm_temporary / oact | TR2026 V.A2 | Calendar year Y | Temporary-or-unlawfully-present inflow, stayer timing to capture | 2026 | to capture | available / control |
| imm_stock / acs | Annual 1-year PUMS; published variable dictionaries | Recent-arrival population with declared YOEP window | Age/sex/citizenship/duration and registered joints | 2014 | to capture | available / reference |

| Component | Fitted or captured support | Rule outside support — proposal unless stated |
| --- | --- | --- |
| ACS donor/packet fit | 2010–2013 annual recent-arrival observed stocks; exact age/household/GQ support to document without scoring2014. | Refuse or frozen coarsening/pooling ladder; never borrow 2014 or invent absent arrival-unit links. |
| migration controls | TR2026 calendar-year controls through 2100; universe and timing bridge not yet admitted. | Refuse beyond captured years or unresolved component bridge. |

Access: `acs`, `oact`, `census2023` in the access table below. Each record carries the full source access fields in JSON; all data-file checks remain unverified.

### Proposals and open questions

- Use household/subfamily units only where observed relationships determine links; unknowns remain explicit.
- Keep same-year exit handling component-specific; an annual stayer control needs inverse-survival/partial-exposure reconciliation, not an unadjusted second mortality/emigration filter.

- Which recent-arrival YOEP window and joint cell family are ratified?
- What resident/SSA-area bridge, arrival-unit rule, parity imputation and family-exit policy does Max approve?
- What blinded documentation/counts will establish recent-arrival power?
- Does the OP3 timing bridge consume Census 2023 emigration assumptions fitted upstream on2014? Choose disjoint assumption source or narrower conditional/regression admission before any claimed independent2014 score.

Evidence for this record:

- 5c82dbd9:docs/design/open_population.md:159-160,291-363
- src/populace_dynamics/engine/entrant_schedule.py:14-22,37-48,359-371
- scripts/build_gate2b_floors.py:818-872
- scripts/build_gate2c_floors.py:1031-1069
- src/populace_dynamics/data/u2_source_registry.py:1-3,26-28
- https://www2.census.gov/programs-surveys/acs/tech_docs/pums/ACS2014_PUMS_README.pdf
- https://www.ssa.gov/oact/Downloadables/CY/index.html
- docs/progress.md:331
- docs/progress/progress.json:115

## Emigration check (OP4)

**`emigration_check` — draft.** Verification: accounting conformance and report only composition. Exit totals aligned to V.A2 outflows; no independent exit-composition claim. EMIGRATION_UNIDENTIFIED remains in force.

### Sources, variables and population

- oact: TR2026 V.A2 outflow components, capture pending.
- census2023: 2023 national projections November methodology pp.11–12; candidate emigration assumption source, not observed exits.
- acs: 2015–2019 annual arrival-cohort stock decline diagnostic, after mortality adjustment; not an exit panel.

- Exit age, sex, nativity, duration since entry and declared family/individual exit unit; separate death and emigration events.
- Census residual cohort emigration assumptions and V.A2 component outflow; no status-adjustment-as-exit substitution.

Population: Surviving resident roster after the year's mortality draw; family units and recent entrants need a prospective risk-set rule. Exited persons retain a distinct abroad/insured-history marker; benefits abroad remain a named gap.

Universe bridge:

- Census resident population/foreign-born residual assumptions differ from Social Security area V.A2 outflows. A registered universe bridge must determine covered roster and controls; do not scale by an invented ratio.
- ACS cohort attrition also reflects death, coverage, return migration, entry-year reporting and sampling; it does not identify individual exits or an unrestricted emigration hazard.

Date mapping:

- Propose emigration at the post-mortality, pre-aging exit step; deaths first, survivors eligible for one exit only. Year Y exit counts map to calendar-year V.A2 outflow.
- Recommend incumbents face a declared annual exposure and new entrants a component-specific partial exposure; whether any entrant can exit in entry year remains for Max/coordinator.
- A component defined as year-end stayers cannot face a second raw full-year survival filter. OP3's timing bridge must reconcile that control to this convention.

### Exposure and partition

- No repository US emigration law found by approved design (engine/entrant_schedule.py:359-371); accountant's exit enum is not an empirical law.
- Census 2023 methodology uses ACS 2015–2019 residuals and 2017 projection rates based on ACS 2011–2015; using these assumptions consumes those underlying years for any purported independent exit check.
- U2 upstream ACS 2015, 2017, 2019 weight calibration is additional indirect exposure. No exit holdout demonstrated.

No held-out year proposed: this record is conformance, sensitivity or report-only.

Fit years:

- Census candidate assumptions upstream ACS 2011–2015 and 2015–2019; overlap with proposed diagnostic.

Overlaps:

- with: gate_pop / gate_entrant_earn (OP0.2); years: [2019]; reason: Shared ACS 2019 cohort stocks; if used here, both registrations must disclose, and exit diagnostic cannot be counted as independent of Census assumption construction.
- with: Track B J; years: []; reason: Unrecorded; coordinator must review all source/family overlaps.

Registry rule: J first; no year cleared by absence from incomplete registry.

Diagnostic years:

- 2015
- 2016
- 2017
- 2018
- 2019

Finding: No admissible holdout established; EMIGRATION_UNIDENTIFIED. Diagnostic years are not claimed held out.

Registry: `daf02425:docs/design/track_b_holdout_registry.json`, SHA-256 `084b8d50ba3c0fe7cf9bd70e3c7c700c60ae682644ead99cca2bb116bfb2ef88`; J candidates absent; recheck merged commit/hash before freeze.

### Cells, tolerance and uncertainty

| Cell | Estimand | Eligibility |
| --- | --- | --- |
| exit_totals | Calendar-year V.A2 outflow by declared category and universe. | Control/bridge available; conformance only. |
| composition | Age×sex×nativity×duration exit pattern and ACS arrival-cohort decline net of mortality. | Report-only; not independently identified. |

| Reference | Tolerance class | Prospective procedure |
| --- | --- | --- |
| oact | administrative_aggregate_control | Conformance in target units within selection-resolution floor plus numeric rounding/summation tolerance to pin. |
| census2023 | assumption_not_observation | No empirical sampling-floor class applies to a forecast assumption; expose sensitivity only. |
| acs | survey_microdata_diagnostic | Proposal from design §5.3: \|ln(candidate/reference)\|; survey-design replicates where available, otherwise household-disjoint half-splits; round(mean + 4*sd, 3), at least 20 events on the weaker half, stabilized tolerance <= ln(1.5). A fixed prospective pooling ladder partitions ineligible cells as report-only. Zero references require a separately registered absolute-scale rule. |

All numeric allowances remain proposals requiring blinded review. No empirical confidence interval or pass verdict for an unidentified exit composition. Survey-based cohort diagnostics may use design-respecting simultaneous95% bounds, with reference/estimation/candidate/MC uncertainty kept separate; those bounds do not identify exits. Insufficient precision stays inconclusive. Accounting conformance is exact in counts and within reported summation residual in weights.

Candidate uncertainty: Preserve fixed family clusters in exit units; propagate donor/OP5-start design uncertainty only when that is the actual run's start; include mortality estimation, cohort-survival, coverage/date bridge and simulation uncertainty. For current unidentified exit composition, publish sensitivity envelopes rather than a false sampling confidence interval around a chosen assumption.

Pass conjunction:

- Exact distinct event kinds; no person both dies and emigrates; emigrating spouse never creates widowhood; emigration-off deaths/survivors unchanged.
- Aligned outflows meet target-unit resolution tolerance and universe/timing bridges. Conformance admits no exit composition.
- Composition has no pass verdict until separately authorized independent holdout and >=0.90 power are established.

### Power procedure

**Identifiability-first cohort-residual sensitivity and exit-conformance simulation.** Status: `not_run_no_real_data`. No empirical exit gate is powered because exits are unidentified. Proposal: demonstrate detection of each injected double exit, death relabel and duplicate-survival error on invented rosters; any future composition gate requires >=0.90 full-conjunction operating characteristic.

Required inputs:

- Invented family rosters and tagged death/exit events; component controls; exit-exposure rule; plausible mortality/coverage/return-migration scenarios.
- For a future gate: independent exit observations, survey covariance and event counts disjoint from assumptions; currently absent.

Procedure:

- Inject accounting faults into invented annual journals and verify deterministic refusal.
- For cohort diagnostics, simulate invented attrition under separate death, emigration, return and coverage channels; show nonidentification rather than interpret residual as observed exit.
- Do not register composition as a gate without new independently admissible source and prospective review.

### Targets and fitted support

| Entry/source | Table | Row | Column | Vintage | Byte hash | Status/role |
| --- | --- | --- | --- | --- | --- | --- |
| em_outflow / oact | TR2026 V.A2 | Calendar year Y | LPR / temporary-or-unlawfully-present outflow, exact headers to capture | 2026 | to capture | available / control |
| em_census_assumption / census2023 | 2023 methodology pp.11–12; rate extract to locate | Age/sex/Hispanic-origin/recent-vs-earlier-arrival strata | Foreign-born residual emigration assumption | 2023 | to capture | validation_only / candidate_assumption |
| em_independent_exits / acs | No independently observed exit table established | ACS cohort decline2015–2019 | Exit hazard independent of death/coverage/return migration | 2015–2019 | to capture | not_available / reference |

| Component | Fitted or captured support | Rule outside support — proposal unless stated |
| --- | --- | --- |
| exit law | Census residual-assumption strata documented; no independently fitted resident exit law admitted. | Propose refuse unsupported strata or publish preregistered constant-rate/pooled sensitivity. Max chooses family/individual units and continuation; not silently extrapolated. |

Access: `oact`, `census2023`, `acs` in the access table below. Each record carries the full source access fields in JSON; all data-file checks remain unverified.

### Proposals and open questions

- Keep EMIGRATION_UNIDENTIFIED and composition report-only.
- Recommend post-death emigration with component-specific exposure; freeze entry-year eligibility jointly with OP3 after the no-double-filter differential check.

- Can any documentation-only source establish independently admissible exit observations? None found.
- Which family exit unit and same-year entrant risk rule does Max approve?
- How are SSA-area outflows bridged to residents and insured emigrants retained for later totals?

Evidence for this record:

- 5c82dbd9:docs/design/open_population.md:161,350-363,464-483
- src/populace_dynamics/engine/entrant_schedule.py:359-371
- https://www2.census.gov/programs-surveys/popproj/technical-documentation/methodology/methodstatement23.pdf pp.11-12

## Demographic target manifest (OP6)

**`demographic_target_manifest` — draft.** Verification: production integrity. Fresh aligned replay at fixed person weights, with whole-unit selection for births/emigration and immigration by construction; mortality consumed from its owner. Alignment demonstrates no transition-law validity.

### Sources, variables and population

- oact: TR2026 V.A1 TFR,V.A2 immigration/outflow,V.A3 July 1 stocks,V.A4 mortality summary, period q by age/sex and CY single-age population catalog; capture metadata pending.
- cbo: Repository CBO 2026 long-horizon single-age fertility by nativity; source identity cited through provenance, not opened data.
- nchs: NCHS 2024 derived single-age baseline shape, exposed; bridge only, not published OACT age schedule.

- Births/ASFR by maternal age, gross positive immigration and emigration category, population stocks by age/sex; nativity only where publisher releases it.
- OACT period death probabilities recorded as mortality-lane target, never OP6 selection target. V.A3/V.A4 and single-age population are validation-only unless a separately reviewed purpose is approved.

Population: Named resident/SSA-area roster after source-specific universe bridges; each selected event unit preserves fixed trajectory weights and relational consistency.

Universe bridge:

- Every margin names resident versus Social Security area; no claim 'aligned to OACT' without a registered bridge.
- TFR is a sum of single-age fertility rates, not an age-specific birth-count control. Convert only through a registered derived shape and exposure denominator.
- Deaths belong to mortality lane SM under d1922. OP6 consumes the chosen mortality adapter identically in both replays and cannot select/reweight deaths.

Date mapping:

- V.A1 fertility and V.A2 flows are calendar-year quantities; compare annual event journals under registered exposure convention.
- V.A3 July 1 and CY Jan 1/July 1/Dec 31 single-age series are stock reference dates, not interchangeable annual totals. Register a within-year stock bridge or mark unavailable.
- V.A4/period q use age/sex/year definitions captured from metadata; mortality lane owns timing and implementation.

### Exposure and partition

- V.A1/V.A4 and OACT q already captured by data/tr2026.py:3-4; CBO 2026 fertility shapes already pinned in provenance.
- NCHS 2024 baseline shape is selected/exposed. V.A2 control semantics already appear in entrant_schedule; native V.A2/V.A3 readers absent.
- Official CY catalog establishes a published single-age population series, correcting a possible inference from V.A3's coarse ages. No population data opened.
- Prior use is reported, not merely proposed: docs/progress.md:331 and docs/progress/progress.json:115 record a 2026-09-06 report-only entrant schedule, a captured/hash-pinned Trustees immigration table and certified-frame donor feasibility check. Current missing native readers do not establish historical nonuse; exact source cells/controls in that older run remain uninspected here.

No held-out year proposed: this record is conformance, sensitivity or report-only.

Fit years:

- Not a scientific gate; control sources are exposed scenario inputs.

Overlaps:

- with: gate_birth / gate_imm / emigration_check / gate_pop; years: []; reason: Manifest controls may enter candidate arms; they cannot independently validate those same margins. All scientific gate runs remain unaligned.

Registry rule: J first; no year cleared by absence from incomplete registry.

Registry: `daf02425:docs/design/track_b_holdout_registry.json`, SHA-256 `084b8d50ba3c0fe7cf9bd70e3c7c700c60ae682644ead99cca2bb116bfb2ef88`; J candidates absent; recheck merged commit/hash before freeze.

### Cells, tolerance and uncertainty

| Cell | Estimand | Eligibility |
| --- | --- | --- |
| birth_selection | Birth total by selected maternal-age margin derived from named TFR/shape bridge. | Only when bridge and target units frozen. |
| exit_selection | Outflow by category at fixed weights and declared exit units. | Requires OP3/OP4 universe/timing bridge. |
| mortality_ownership | No OP6 death selection; both replays use mortality owner's adapter. | Required conformance. |

| Reference | Tolerance class | Prospective procedure |
| --- | --- | --- |
| oact | administrative_scenario_control | Selection-resolution floor in native target units plus pinned numeric rounding/summation allowance; exact numeric values/corridors remain open. |
| cbo | published_scenario_assumption | No empirical sampling floor; capture rounding and concept mapping for scenario integrity. |
| nchs | administrative_and_vital_statistics_aggregates | Exposed derived-shape input. No manufactured sampling floor. Before lock, pin an allowance for same-target-year revision/vintage dispersion, measurement/concept/coverage bridges and half the published rounding unit. Variation between outcome years is not measurement uncertainty. Numeric allowance remains unset; this blocks freeze. |

All numeric allowances remain proposals requiring blinded review. Nongate production integrity: selection-resolution floor plus target-unit numeric tolerance, no empirical sampling floor around scenario controls and no scientific confidence interval for alignment. Separate actual start/donor/fit/seed uncertainty in any comparative report; raw displacement until corridors approved.

Candidate uncertainty: Production-integrity replay reports seed/whole-unit selection resolution and matched-start/displacement sensitivity; it does not use a confidence interval to claim aligned transition accuracy. If comparing scenarios, propagate the actual start/donor/fit uncertainty and coupled seeds; never use OP12 held-out outcomes to fit targets or corridors.

Pass conjunction:

- Target status/hash/universe/date/units all explicit; unavailable targets not invented.
- Selectable margins within resolution floor plus pinned numeric tolerance; exact count identities and reported summation residual; no person weight changes.
- Unaligned artifact byte-identical with aligned producer importable or absent; no death selected/reweighted/relabelled; emigrating spouse never widows survivor.
- Complete margin/year/stratum displacement table distinguishes zero and unavailable, publishes displaced set; corridor_status=not_available until prospectively authored.

### Power procedure

**Selection-resolution and replay fault-injection conformance analysis.** Status: `not_run_no_real_data`. No empirical power claim. Demonstrate each preregistered target-unit/ownership/isolation fault is detected deterministically; prospectively assess whether discrete resolution permits the requested corridor.

Required inputs:

- Invented weighted family rosters/event units; target-unit metadata; candidate selection resolution; numeric precision and corridor proposals; coupled seeds.

Procedure:

- Vary invented weights/control scales and derive reachable whole-unit residuals without changing person weights.
- Inject death selection, weight changes, missing strata and unaligned-import contamination; require rejection.
- No production release before target-unit tolerance and corridor review; 0.90 empirical requirement is not applicable to this nongate.

### Targets and fitted support

| Entry/source | Table | Row | Column | Vintage | Byte hash | Status/role |
| --- | --- | --- | --- | --- | --- | --- |
| tr_tfr / oact | TR2026 V.A1 | Calendar year Y | Intermediate/low/high TFR | 2026 | to capture | available / control |
| tr_single_age_fertility / oact | No public single-age fertility series established in inspected CY catalog | Maternal single age×year | ASFR | 2026 | to capture | not_available / bridge_required |
| nchs_shape_bridge / nchs | Repository derived interpolation from 2024 ASFR bands | Ages14–49 | Normalized age shape scaled to V.A1 TFR | 2024/2026 | to capture | available / proposed_bridge_not_oact_observation |
| cbo_shape_bridge / cbo | Pinned CBO 2026 single-age fertility catalog in provenance | Maternal age×nativity×year | ASFR | 2026 | to capture | available / alternative_bridge_requires_ratification |
| tr_inflow / oact | TR2026 V.A2 | Calendar year Y | LPR plus temporary-or-unlawfully-present gross inflow | 2026 | to capture | available / control |
| tr_outflow / oact | TR2026 V.A2 | Calendar year Y | Outflow components, exclude adjustment of status | 2026 | to capture | available / control |
| tr_population / oact | TR2026 V.A3 | July 1 Y; under20/20–64/65+ | Population and dependency ratios; no nativity | 2026 | to capture | validation_only / reference |
| tr_single_age_population / oact | CY population catalog | Single age×sex×marital status×year | Jan 1/July 1/Dec 31 population; actual header to capture | 2026 catalog vintage to verify | to capture | validation_only / reference |
| tr_mortality_summary / oact | TR2026 V.A4 | Year×sex | Life-expectancy summary, exact columns to capture | 2026 | to capture | validation_only / reference |
| mortality_lane_q / oact | OACT period death probabilities / CY catalog | Single age×sex×year | Period q | 2026 | to capture | available / mortality_lane_target_no_op6_selection |

| Component | Fitted or captured support | Rule outside support — proposal unless stated |
| --- | --- | --- |
| fertility margin bridge | NCHS 2024 derived shape ages 14–49, or pinned CBO rates2021–2099 by nativity. | Max/coordinator chooses registered bridge; OACT unsupported single-age fertility remains not_available. Refuse undeclared extensions. |
| demographic controls | TR2026 calendar years through 2100; each manifest's captured range to verify. | Refuse absent years/statuses, not interpolate silently. |

Access: `oact`, `cbo`, `nchs` in the access table below. Each record carries the full source access fields in JSON; all data-file checks remain unverified.

### Proposals and open questions

- Recommend retain baseline derived shape as explicit exposed bridge unless Max chooses separately pinned CBO; do not label it published OACT single-age fertility.
- Use OACT CY single-age population for validation-only stock margins once vintage/date/universe pinned. No coarse-age disaggregation needed for that documented series.

- Which fertility bridge and native target units/corridors are ratified?
- Can coordinator locate a published OACT single-age fertility release without reading restricted tables?
- Which metadata capture lane pins all target bytes and source-specific terms?

Evidence for this record:

- 5c82dbd9:docs/design/open_population.md:163,325-363,424-435
- src/populace_dynamics/data/tr2026.py:3-4
- data/external/tr2026/provenance.md:54
- data/external/cbo2026/provenance.md:29-56
- src/populace_dynamics/baselines/tr2026_intermediate.py:84,165-168
- https://www.ssa.gov/oact/Downloadables/CY/index.html
- https://www.ssa.gov/oact/tr/2026/lrIndex.html
- gates.yaml:1298
- docs/baselines.md:555-557
- src/populace_dynamics/baselines/cbo2026_long_term.py:330
- src/populace_dynamics/baselines/tr2026_intermediate.py:245
- docs/progress.md:331
- docs/progress/progress.json:115

## Population record (OP7)

**`gate_pop` — draft.** Verification: retrodiction conditional on frozen arm. Unaligned2013→2020 population composition by sex/five-year age and 2019 foreign-born period-of-entry stock, under declared date/universe bridges. Exposed2020 estimands are regression evidence.

### Sources, variables and population

- acs: 2013 annual1-year PUMS start;2019 annual1-year PUMS foreign-born period-of-entry target.
- census2020: 2020 Census age/sex counts at April 1, 2020; exact table to select without reading values.2020 DA coverage release March 10, 2022 proposed coverage allowance.
- popest: 2013 resident estimates report-only; exact vintage unresolved.

- Census sex×five-year age groups built from documented single-age counts, no guessed table labels.
- ACS NATIVITY,CIT,YOEP,AGEP,SEX,TYPE,PWGTP and replicate weights;2013 RELP to 2019 RELSHIPP concept map.
- Start reference date, group-quarters strata and deterministic spouse/parent links only where observed relationship identifies them.

Population: OP5 national ACS 2013 demographic roster with separate household and institutional/noninstitutional GQ strata. Exact matched resident universe and unknown links remain explicit.

Universe bridge:

- Recommend preserve GQ mass separately; household-only link reconstruction cannot stand for total residents. ACS two-month residence differs from decennial usual residence.
- DA coverage includes all residents and provides sex/single-age coverage ranges; PES excludes all GQ and Remote Alaska and supplies survey SEs. Pin matched DA cells/ranges for full resident age/sex margin, not one unmatched PES national percentage.
- Existing2020 multigenerational facts are exposed; unused age/sex census cells still require coordinator exposure review, not an independence claim based on different table name.

Date mapping:

- Proposal OP5 reference date July 1, 2013, with ACS calendar-year interviews bridged by explicit interview-age/exposure uncertainty; ACS does not itself represent July 1. No invented interview dates treated as observed.
- Census target is April 1, 2020. Recommend a registered within-year stock/exposure bridge from annual event journals; without monthly dates use a declared interpolation/exposure sensitivity and bound its error, not relabel December31 as April 1.
- ACS 2019 target is calendar-year collection: compare a registered exposure-weighted mixture of2019 projection states/ages, with bounds when collection timing is unavailable, not one unqualified annual snapshot.
- 2013 report-only population estimates use July 1 reference with own vintage; bridge separately.

### Exposure and partition

- Census 2020 multigenerational household figures already cited in baseline/floor anchors: data/external/census_gate2b_anchor_sources.md:50-64; scripts/gate2b_anchor_decomposition.py:59,253-265.
- U2 documents upstream ACS 2019 calibration, so2019 foreign-born target is indirectly exposed to a shared data source even though no PUMS reader found; specific outcome nonuse unresolved.
- ACS 2013 start and OP3's2010–2013 donor fit share inputs; this is candidate-side dependence, not an independent reference comparison.
- Census estimates Vintage 2007/2008 previously used for DI denominators;2013 vintage must be audited separately.
- Vintage 2013 methodology says population estimates control ACS/CPS. The2013 estimates check is a shared-upstream report-only consistency check, not independent validation of the ACS start.
- Microcosm frame documentation names ACS as an upstream source without identifying years/estimands (docs/infrastructure.md:104-106; docs/methodology.md:9-11; docs/funder-summary.md:174-175). Frame-based prior uses cannot clear ACS 2010–2019 without upstream provenance, even if this checkout has no PUMS reader.

| Source | Tentative year | Status | Reason |
| --- | --- | --- | --- |
| census2020 | 2020 | pending_registry | Tentative sex/age target only; related2020 household estimands exposed. Independent status unresolved. |
| acs | 2019 | pending_registry | Tentative foreign-born period-of-entry target; upstream ACS 2019 calibration and OP4/OP8 overlap require disclosure. |

Fit years:

- 2013

Overlaps:

- with: gate_imm; years: [2013]; reason: Shared start/donor fit; gate_imm's2014 score remains separately fenced.
- with: emigration_check; years: [2019]; reason: Shared ACS 2019 cohort stocks; Census 2023 assumptions also use2015–2019; diagnostic not independent.
- with: gate_entrant_earn (OP0.2); years: [2019]; reason: Same ACS annual file and arrival cohorts; both registrations must disclose and limit independence claims.
- with: Track B J; years: []; reason: J absent; choice and source-family relations await coordinator.

Registry rule: J first; no year cleared by absence from incomplete registry.

Exposure disposition: Recommend regression label on exposed2020 facts and conservative unresolved exposure label on unestablished cells; do not claim pristine2019/2020 holdouts.

Registry: `daf02425:docs/design/track_b_holdout_registry.json`, SHA-256 `084b8d50ba3c0fe7cf9bd70e3c7c700c60ae682644ead99cca2bb116bfb2ef88`; J candidates absent; recheck merged commit/hash before freeze.

### Cells, tolerance and uncertainty

| Cell | Estimand | Eligibility |
| --- | --- | --- |
| census_age_sex | Resident population by sex×five-year age at April 1, 2020; terminal-age group fixed before scoring. | Matched coverage product, all strata and date bridge available. |
| foreign_born_entry | Foreign-born population/share by frozen entry-period groups in calendar-year 2019. | ACS design support and frozen pooling ladder; unknown YOEP explicit. |

| Reference | Tolerance class | Prospective procedure |
| --- | --- | --- |
| census2020 | census_counts | Pin2020 Demographic Analysis net-coverage-error low/middle/high range for the matched resident age/sex cell and add declared concept/date/disclosure-avoidance/rounding allowance. Do not interpret DA range as a sampling SE. Numeric allowance unset; no freeze. |
| acs | survey_microdata | Proposal from design §5.3: \|ln(candidate/reference)\|; survey-design replicates where available, otherwise household-disjoint half-splits; round(mean + 4*sd, 3), at least 20 events on the weaker half, stabilized tolerance <= ln(1.5). A fixed prospective pooling ladder partitions ineligible cells as report-only. Zero references require a separately registered absolute-scale rule. |
| popest | administrative_estimate_report_only | No manufactured sampling floor. Before lock, pin an allowance for same-target-year revision/vintage dispersion, measurement/concept/coverage bridges and half the published rounding unit. Variation between outcome years is not measurement uncertainty. Numeric allowance remains unset; this blocks freeze. |
| oact | assumption_control_if_realized_arm | Scenario input; not independent empirical validation. |
| census2023 | assumption_if_exit_source | Document upstream ACS uses; sensitivity, not observation floor. |

All numeric allowances remain proposals requiring blinded review. Simultaneous 95% confidence bounds with Bonferroni over the frozen cell family; include reference, estimation, design and simulation uncertainty. Monte Carlo standard error below one-tenth of each tolerance. Insufficient precision is inconclusive. Never drop a failed/unsupported cell after outcomes.

Candidate uncertainty: Resample actual OP5 household units under ACS design, GQ persons separately; couple OP3 donor resamples and shared2013 construction; refit fitted fertility/marital/exit inputs only within declared fit support; include mortality-lane uncertainty, start-date/GQ/April 1/calendar-year bridge uncertainty and simulation seeds. Census reference coverage uncertainty remains distinct from candidate resampling.

Pass conjunction:

- Each registered eligible2020 age/sex and 2019 entry-period bound lies inside its source-specific tolerance; no dropping unsupported cells.
- Fixed unaligned run/arm, weights and source vintages; date/universe/GQ/link conventions pass conformance; MC precision requirement met.
- A realized-control arm admits composition conditional on those controls only. Regression/unresolved exposure cannot support independent predictive admission.

### Power procedure

**Clustered retrodiction equivalence simulation with census-coverage envelope.** Status: `not_run_no_real_data`. Proposal: require >=0.90 full-conjunction admission probability under prospectively named in-margin scenarios (including exact agreement and reviewer-chosen near-margin profiles), with a simulation interval precise enough for the review. Effect sizes, tolerances and cell family must be frozen before outcomes. Separately estimate false-admission probability for prespecified out-of-margin profiles; no admission or inconclusive alone is not evidence the procedure detects a wrong mechanism. No power demonstrated.

For frozen empirical cells j with discrepancy d_j=|ln(C_j/R_j)| and prospective tolerance delta_j: H0 is at least one d_j >= delta_j; H1 is all d_j < delta_j. A separately registered absolute discrepancy replaces log ratio for zero cells. Full-conjunction admission power is P(all simultaneous intervals inside their margins) under a named in-margin alternative, not probability of inconclusive.

Required inputs:

- Blinded or published matched ACS 2013/2019 effective sizes/design covariance; OP3 donor support; census coverage-product cell ranges.
- Fitted-law variance and seed variance, shared-start covariance, household/GQ units, date-mapping and realized-control arm assumptions; fixed critical cells/tolerances.

Procedure:

- Build invented weighted household/GQ starts and simulate to one fixed2020 gate horizon; compare matched April 1 and calendar-year 2019 projections.
- Nest candidate resampling/refits and reference coverage envelope; perturb births/flows/timing in prespecified profiles.
- Estimate full-conjunction operating characteristic/MC interval; inadequate sample information, coverage bridge or >=0.90 feasibility blocks review approval.

### Targets and fitted support

| Entry/source | Table | Row | Column | Vintage | Byte hash | Status/role |
| --- | --- | --- | --- | --- | --- | --- |
| pop_2020_age_sex / census2020 | 2020 Census DHC PCT12: Sex by Single-Year Age | Sex×single year age; aggregate to prospective five-year groups | April 1, 2020 usual-resident population count | 2020 Census DHC release2023 | to capture | available / reference |
| pop_2020_coverage / census2020 | 2020 National Demographic Analysis coverage tables | Matched sex×single age/five-year group | Low/middle/high net coverage error | March 10, 2022 release | to capture | available / tolerance_input |
| pop_2019_entry / acs | 2019 annual1-year PUMS; dictionary NATIVITY/YOEP | Foreign-born by declared entry period | Weighted stock/share and design replicates | 2019 | to capture | available / reference |
| pop_2013_check / popest | Vintage 2013 national/state/PuertoRico population estimates; exact output series to capture | July 1, 2013 resident population (DATE=6 metadata) | Total/age/sex product to pin | Vintage 2013 | to capture | validation_only / reference |

| Component | Fitted or captured support | Rule outside support — proposal unless stated |
| --- | --- | --- |
| retrodiction laws and assumptions | Proposed2013-vintage information set through registered fit boundary; exact fertility/marital/mortality/exit supports not yet frozen. | Refuse law without declared support/continuation. Exposed NCHS or realized controls need separately labeled conditional/regression arm. |

Access: `acs`, `census2020`, `popest`, `oact`, `census2023` in the access table below. Each record carries the full source access fields in JSON; all data-file checks remain unverified.

### Proposals and open questions

- Recommend a fitted-law arm with only demonstrably available2013-vintage assumptions as primary feasibility question; retain realized aggregate controls as a separately labeled composition diagnostic. Max must choose arms.
- Recommend July 1, 2013 start, separate GQ strata, and explicit April 1/calendar-year bridges with sensitivity bounds; these are proposals, not conventions already frozen.

- Can a genuinely2013-vintage control/fit set be pinned? If not, which realized-control arm may register and with what narrower scope?
- Which exact census product/table and matched DA coverage allowance does Max approve?
- Can coordinator resolve2020/2019 exposure, including upstream ACS calibration and shared OP0.2 use?

Evidence for this record:

- 5c82dbd9:docs/design/open_population.md:162,164,291-363
- data/external/census_gate2b_anchor_sources.md:50-64
- scripts/gate2b_anchor_decomposition.py:59,253-265
- https://www.census.gov/programs-surveys/decennial-census/about/coverage-measurement/da.html
- https://www.census.gov/programs-surveys/decennial-census/about/coverage-measurement/similarities-differences-da-pes.html
- https://www.census.gov/newsroom/blogs/random-samplings/2022/03/period-estimates-american-community-survey.html
- https://www.census.gov/data/tables/2023/dec/2020-census-dhc.html
- https://www2.census.gov/programs-surveys/popest/technical-documentation/methodology/2010-2013/2013-natstcopr-meth.pdf
- https://www.census.gov/data/developers/data-sets/popest-popproj/popest/popest-vars.Vintage_2013.html

## Demographic horizon record (OP10a)

**`demographic_horizon` — draft.** Verification: mechanics and conditional sensitivity. One production horizon to 2100 for TR2026, shorter outputs read as prefixes. Every year past2030 conditional on named assumptions, never validated. OP11a comparisons report agreement/disagreement only.

### Sources, variables and population

- oact: TR2026 intermediate/low/high demographic assumptions through 2100 and CY single-age population catalog, captured vintages to pin.
- cbo: Pinned long-horizon fertility/mortality baseline plus January 2026 demographic-outlook documentation; distinguish each release/horizon.
- census2023: 2023 main/alternative immigration projection series, methodology through 2100; nativity Table 8 catalog.

- Single-age/sex population, births by maternal age and nativity where available, deaths, gross inflow/outflow, fitted demographic states and assumption identifiers.
- OP11a2050/2065/2070: OACT V.A3 three broad age groups, no nativity; Census 2023 Table 8 nativity and Tables 9/10 nativity×selected ages; CBO requested population-nativity margins not established.

Population: Same explicitly bridged resident/SSA-area roster as registered production inputs. Report each publisher only on its published universe, reference date and dimensions; no fabricated nativity for OACT or unavailable CBO cells.

Universe bridge:

- OACT/CBO Social Security area and Census resident populations differ. Publish separate like-for-like comparisons after approved bridge; do not call the same unbridged stock agreement.
- No alignment of mortality here: same mortality-lane adapter for both replays, with uncertainty/assumption path specified. Census mortality/migration assumptions are comparative scenarios, not observations.

Date mapping:

- Register production end year 2100 for TR2026; shorter horizons use prefixes of that run because scheduled entrants affect newborn ordinals under the existing engine.
- Census 2023 base July 1, 2022 and annual July 1 series map to July 1 outputs; OACT V.A3 July 1 likewise. CY catalog also offers Jan 1/Dec 31; choose matching snapshot before comparison.
- 2050, 2065, 2070 are comparison dates, not proof of independent validation. CBO source's calendar-year/reference-date mapping remains to capture for any admitted margin.

### Exposure and partition

- TR2026 NCHS 2024 shape and CBO single-age fertility/mortality baseline already selected/captured; all scenarios are exposed assumptions.
- Census 2023 emigration methodology upstream ACS 2011–2015/2015–2019; disclose shared inputs, not an independent truth series.
- Approved design documents horizon-dependent newborn streams, docs/design/open_population_evidence/horizon_dependence.py. No run or output was opened or executed in this audit.
- Prior use is reported, not merely proposed: docs/progress.md:331 and docs/progress/progress.json:115 record a 2026-09-06 report-only entrant schedule, a captured/hash-pinned Trustees immigration table and certified-frame donor feasibility check. Current missing native readers do not establish historical nonuse; exact source cells/controls in that older run remain uninspected here.

No held-out year proposed: this record is conformance, sensitivity or report-only.

Fit years:

- Each component's empirical training support below; future scenario assumptions are not holdouts.

Overlaps:

- with: gate_birth / gate_pop / OP0.2; years: []; reason: Shares demographic laws/controls and near-term admissions; report-only long-horizon agreement cannot rescue failed/unresolved gates.

Registry rule: No empirical future holdout reserved; any future retrospective test must follow J-first coordinator registry procedure.

Registry: `daf02425:docs/design/track_b_holdout_registry.json`, SHA-256 `084b8d50ba3c0fe7cf9bd70e3c7c700c60ae682644ead99cca2bb116bfb2ef88`; J candidates absent; recheck merged commit/hash before freeze.

### Cells, tolerance and uncertainty

| Cell | Estimand | Eligibility |
| --- | --- | --- |
| mechanics | Constant-rate/no-migration two-sex Leslie expected age-sex distribution and dominant-eigenvalue growth. | Invented constant-rate support and exact engine timing matched. |
| support | Every component query has explicit supported domain or continuation rule. | Required; EXTRAPOLATION_UNDECLARED refusal on missing rule. |
| comparisons | 2050/2065/2070 publisher dimensions in target manifest. | Report-only; unavailable dimensions remain unavailable. |

| Reference | Tolerance class | Prospective procedure |
| --- | --- | --- |
| oact | scenario_assumptions_not_observed_future | No empirical reference floor; capture rounding/date/universe metadata. Mechanics residual must lie within MC interval plus pinned floating-point residual. |
| cbo | scenario_assumptions_not_observed_future | Report sensitivity, no predictive pass tolerance. |
| census2023 | scenario_assumptions_not_observed_future | Report conditional comparison, no predictive pass tolerance. |

All numeric allowances remain proposals requiring blinded review. Future assumptions have no empirical truth interval. Separate scenario sensitivity from candidate start/donor/estimation/seed uncertainty. Invented Leslie differential comparisons use simultaneous95% Monte Carlo bounds, Bonferroni over frozen mechanics cells and MC error below one-tenth of mechanics tolerance.

Candidate uncertainty: Separate stochastic seed/estimation/start/donor uncertainty from structural assumption-path sensitivity; use actual start design, shared family clusters and fitted-law resampling. A scenario envelope is not a probability interval over future truth. A Leslie differential test uses only invented rates/start; simulation mean precision meets its prospectively pinned tolerance.

Pass conjunction:

- Prerequisite demographic gate/regression/conformance conditions satisfied within their admitted scope; all production horizon/support refusals enforced.
- Leslie differential mechanics and prefix invariants pass on invented data with declared timing; no empirical future validation claim.
- Each unavailable comparison margin labeled not_available; conditional assumption labels and mortality ownership preserved. No OP10a drift-growth tolerance invented; OP10b limits belong to OP0.2.

### Power procedure

**Invented Leslie differential precision and assumption-sensitivity design.** Status: `not_run_no_real_data`. No future-prediction power claim. Proposal: choose enough independent seeds so simultaneous MC uncertainty is below one-tenth of predeclared mechanics tolerance; injected undeclared-support/horizon/timing faults must be detected. >=0.90 empirical admission requirement applies to any separately proposed backtest, not a future scenario.

Required inputs:

- Invented age/sex start and constant fertility/mortality; independent matrix implementation under engine timing; seed variance.
- All component fit supports/continuations and named assumptions; fixed comparison dates, units, universes and release ranges.

Procedure:

- Independently implement two-sex Leslie recursion and micro draws on invented data, compare per-year expected stocks/growth under Bonferroni bounds.
- Test undeclared extrapolation, changed end-year requests and timing faults fail; repeat seeds only to reach pinned precision.
- Publish structural scenarios separately; no real-data power or invented-data demonstration was run in OP0.1.

### Targets and fitted support

| Entry/source | Table | Row | Column | Vintage | Byte hash | Status/role |
| --- | --- | --- | --- | --- | --- | --- |
| hz_oact_pop / oact | TR2026 V.A3 | 2050, 2065, 2070 July 1 | Under20,20–64,65+; no nativity | 2026 | to capture | validation_only / report_only_comparison |
| hz_oact_nativity / oact | TR2026 V.A3 | 2050, 2065, 2070 | Nativity not published in this table | 2026 | to capture | not_available / report_only_comparison |
| hz_census_nativity / census2023 | 2023 main-series Table 8 catalog | 2050, 2065, 2070; exact worksheet labels to capture | Native/foreign-born population | 2023 | to capture | validation_only / report_only_comparison |
| hz_census_age_nativity / census2023 | 2023 main-series Tables 9/10 catalog | 2050, 2065, 2070; exact rows to capture | Native/foreign-born selected ages as cataloged | 2023 | to capture | validation_only / report_only_comparison |
| hz_cbo_2050_nativity / cbo | January 2026 outlook landing/report catalog | 2050 within2026–2056 standard release | Population by nativity not established; maternal fertility nativity is a different estimand | 2026 release corrected June 2026 | to capture | not_available / requires_documented_product |
| hz_cbo_2065_2070_nativity / cbo | No qualifying longer-horizon population-nativity product established | 2065, 2070 outside inspected standard outlook horizon | Population by nativity | 2026 / alternative release unresolved | to capture | not_available / requires_documented_product |

| Component | Fitted or captured support | Rule outside support — proposal unless stated |
| --- | --- | --- |
| fertility | Candidate16 female person-years; ages 15–49, parity categories0,1,2,3 with 3 meaning3+; probabilities keyed by(age,min(parity,3),birth decade). Training uses age-kernel bandwidth3 and only represented cohort/parity exposure. Committed seed metadata lists decades1880–2000 by 10 for seeds 0,1,2,4 and 1890–2000 for seed 3; no2010+ cohort. Baseline alternatives: derived NCHS 2024 ages 14–49; CBO single-age/nativity 2021–2099. | Historical component initializes absent cells to zero, clips age indices/caps parity and returns zero for unknown cohort. This is existing behavior, not a ratified extrapolation rule for OP2. Recommend refuse unsupported cohort/stratum until Max ratifies a labeled terminal-cohort or other continuation; do not silently claim post 2030 fertility support. CBO 2100 also needs a registered bridge or refusal. |
| marital/household | Existing certified native panel support through 2022; forward B4 support and entrant coverage not yet admitted (approved design §2.4). | No silent native-panel carry-forward as admitted law; require B4 declared forward support and explicit terminal-decade rule, otherwise refuse. |
| mortality | OACT period q catalog and mortality owner's admitted age/year support; exact terminal-age/year handling to pin. | Mortality lane decides adapter/continuation. OP10a refuses missing rule; OP6 does not normalize deaths again. |
| migration | V.A2 calendar-year controls through 2100; Census 2023 resident assumptions use declared strata/base and ACS residual support. | Refuse years past captured support or unresolved age/nativity/duration cells; Max chooses any terminal-bin continuation/family-unit rule. |
| parity/entry packet | Declared seed/donor2010–2013 empirical support; generated future cohorts are scenario extensions. | Preserve unknowns and explicit pooling/out-of-domain markers; never use held-out2014/2019 to fill support after lock. |

Access: `oact`, `cbo`, `census2023` in the access table below. Each record carries the full source access fields in JSON; all data-file checks remain unverified.

### Proposals and open questions

- Recommend freeze one2100 TR production horizon and publish every post 2030 year as conditional, consistent with Max's already approved principle.
- Record Census nativity availability for all three comparison years. Keep CBO requested nativity margins not_available from inspected documentation; ask coordinator to verify a separately documented longer-horizon product before selecting.

- Which component continuation rules does Max ratify, and what support will B4/mortality lane admit?
- Does a separately documented CBO release provide2050/2065/2070 population by nativity? Landing-page silence does not prove global absence; no workbook opened.
- What matrix timing tolerance and seed precision are fixed prospectively?

Evidence for this record:

- 5c82dbd9:docs/design/open_population.md:95-105,140-146,167,170,352-363,444-451,515-540
- data/external/cbo2026/provenance.md:29-56
- https://www.ssa.gov/oact/Downloadables/CY/index.html
- https://www.cbo.gov/publication/61879
- https://www.cbo.gov/publication/61994
- https://www.cbo.gov/recurring-data/57059
- https://www.census.gov/data/tables/2023/demo/popproj/2023-summary-tables.html
- https://www2.census.gov/programs-surveys/popproj/technical-documentation/methodology/methodstatement23.pdf pp.2,11-12
- src/populace_dynamics/models/family_transitions/components/fertility.py:28-45,80-94,123-157,170-194
- src/populace_dynamics/engine/marital.py:352-374
- runs/gate2_hazard_v16.json:8732-8759,12485-12512,16238-16265,19990-20017,23742-23769 (age/parity/cohort metadata only)
- gates.yaml:1298
- docs/baselines.md:555-557
- src/populace_dynamics/baselines/cbo2026_long_term.py:330
- src/populace_dynamics/baselines/tr2026_intermediate.py:245
- docs/progress.md:331
- docs/progress/progress.json:115

## Exposure inventory

Scope: the assigned committed checkout at `b51ffb576090`; code, allowed metadata/provenance and selected aggregate-run metadata. Restricted paths are excluded before byte searches; downloaded data and external working folders stay closed. No repository no-hit clears another lane, external session or uncommitted history. Source years and observed estimands remain distinct from derived shapes and documentary labels.

**NCHS producer.** Final2024 vintage plus2023 cross-check; annual2016–2024 maternal five-year ASFR series; endpoint group definitions and TFR aggregation.2015/SEX/MBSTATE_REC/raw MAGER observations absent from committed selection.

Evidence: `scripts/fetch_nchs_asfr.py:9-25,52-62,82-90,257-293,309-360`.

**NCHS annual-rate reader.** Gate2 floor consumes2016–2023 keys under MAX_YEAR2023; separately compares pooled all/recent fertility to 2024. Ratios reported, not tuned; later structure selection not excluded by that label.

Evidence: `scripts/build_gate2_floors.py:78,626-674,693-743,924-931`; `src/populace_dynamics/data/transitions.py:113`.

**NCHS selected baseline shape.** asfr.py reads2024 rates/TFR and interpolates to ages 14–49; TR2026 default uses nchs2024 and scales annually to OACT TFR. Not unused; interpolation is not observed single-age natality.

Evidence: `src/populace_dynamics/baselines/asfr.py:67-135`; `src/populace_dynamics/baselines/tr2026_intermediate.py:21-28,84,165-168,222-233`.

**NCHS integrity and test consumers.** Read/hash/integrity checks also consume input bytes/structure; their passing does not validate an independent natality target.

Evidence: `scripts/build_gate2_floors.py:696,1222`; `src/populace_dynamics/baselines/common2026.py:25,97,113`; `tests/test_nchs_asfr.py:21`; `tests/test_gate2_floors.py:42,454`; `tests/baselines/test_asfr_and_claim_tables.py:41,49,53,59,73`.

**NCHS input metadata.** Key-only parse: headline tables2023/2024; annual2016–2024; age-group only, with 10–14 in headline table and 15–49 annual bands. No sex/nativity/raw single-age dimension. Hash578742b151d5656231527175e5e4c29c0554ade8bb56807235d6a75890594f60. No rates copied.

Evidence: `data/external/nchs_asfr_2024.json (keys/provenance/hash only)`.

**Other NCHS inputs.** Candidate NCHS life-table uses are mortality, not a second natality source; no additional natality input found in audited corpus.

Evidence: `scripts/run_gate2_candidate5.py:189-194,235-249`.

**ACS proposed floor anchors.** Gate2b/2c nominate ACS PUMS/tables as external-anchor gaps; no PUMS read in those blocks. Later household/living-arrangement/multigenerational and assortative-mating consumers read published aggregate benchmarks.

Evidence: `scripts/build_gate2b_floors.py:818-872`; `scripts/build_gate2c_floors.py:1031-1069`; `scripts/gate2b_anchor_decomposition.py:8-14,55-59`; `scripts/gate2c_anchor_decomposition.py:271,303-307`; `scripts/build_gate_w1_floors.py:649-660,696-704`.

**ACS upstream PSID weights.** Documentary U2 registry describes ACS 2015/2017/2019 calibration, including 2017 one-year PUMS controls. This is indirect calibration exposure even with no repository PUMS reader found.

Evidence: `data/external/track_u2/weights.json:149,337,344,350,424`; `src/populace_dynamics/data/u2_source_registry.py:1-3,26-28,392-394`.

**Census 2020.** Multigenerational household estimands and 2020/2010 comparison previously cited/read. This does not establish national age/sex count exposure; unused status must be decided per estimand plus shared-year registry rule.

Evidence: `data/external/census_gate2b_anchor_sources.md:50-64`; `scripts/gate2b_anchor_decomposition.py:59,253-265,402-404`.

**Population estimates.** Vintage 2007/2008 national monthly single-age/sex resident estimates used as DI denominators; exact2013 product remains unestablished.

Evidence: `scripts/extract_di_asr_2008.py:21-22,241-272,675,863-865`; `src/populace_dynamics/engine/di_entitlement_rates.py:740`.

**V.A2 / V.A3.** V.A2 gross-positive caller-control convention exposed, native readers absent; V.A3 not in captured TR2026 set, no native code consumer found.2008 table V.A3 is a different mortality table/vintage.

Evidence: `src/populace_dynamics/engine/entrant_schedule.py:3-6,37-42,185-200`; `src/populace_dynamics/data/tr2026.py:3-4`; `data/external/tr2026/provenance.md:54`; `data/external/tr2026/sources.json:1`.

**CPS June / Census 2023.** No implemented reader or previous source-use hit established in code corpus; approved design proposes them. Census 2023 methodology read now establishes ACS 2011–2015/2015–2019 upstream exit-assumption uses, including potential2014 exposure through OP3.

Evidence: `5c82dbd9:docs/design/open_population.md:291-307`; https://www2.census.gov/programs-surveys/popproj/technical-documentation/methodology/methodstatement23.pdf pp.11-12.

**Issue42 registrations.** Source-filtered gh issue view inspection found Census household concept/aggregate anchors and NCHS mortality trend registrations, not additional natality/ACS 2010–2019 reads or named use of CPS June, TR2026 V.A2/V.A3, Census 2023 or population estimates. Exact and broader source-name scans were used; no negative search proves external nonuse. Installed gh rejects --comments with --json, so after that failed invocation the comments JSON field was filtered before output. Listed restricted result comment IDs were excluded; displayed numeric text was redacted before inspection.

Evidence: https://github.com/PolicyEngine/microcosm-dynamics/issues/42#issuecomment-4939453260; https://github.com/PolicyEngine/microcosm-dynamics/issues/42#issuecomment-4939456379; https://github.com/PolicyEngine/microcosm-dynamics/issues/42#issuecomment-4911788302; https://github.com/PolicyEngine/microcosm-dynamics/issues/42#issuecomment-4928232089.

**Fertility fitted support (metadata only).** Candidate16 female person-years; ages 15–49, parity categories0,1,2,3 with 3 meaning3+; probabilities keyed by(age,min(parity,3),birth decade). Training uses age-kernel bandwidth3 and only represented cohort/parity exposure. Committed seed metadata lists decades1880–2000 by 10 for seeds 0,1,2,4 and 1890–2000 for seed 3; no2010+ cohort. Historical component initializes absent cells to zero, clips age indices/caps parity and returns zero for unknown cohort. This is existing behavior, not a ratified extrapolation rule for OP2. Recommend refuse unsupported cohort/stratum until Max ratifies a labeled terminal-cohort or other continuation; do not silently claim post 2030 fertility support.

Evidence: `src/populace_dynamics/models/family_transitions/components/fertility.py:28-45,80-94,123-157,170-194`; `src/populace_dynamics/engine/marital.py:352-374`; `runs/gate2_hazard_v16.json:8732-8759,12485-12512,16238-16265,19990-20017,23742-23769 (metadata only)`.

**CPS parity and 2013 estimates documentation now checked.** June 2012/2014 parity codebooks are documented proposals, no outcomes read. June 2012 covers household women 15–50 with children-ever-born/allocation and basic CPS weight.2013 estimates control ACS/CPS, so the ACS-start check remains report-only.

Evidence: https://www2.census.gov/programs-surveys/cps/techdocs/cpsjun12.pdf Attachments3,7,16; https://www2.census.gov/programs-surveys/popest/technical-documentation/methodology/2010-2013/2013-natstcopr-meth.pdf.

**Completed broad corpus check.** Expanded filename-whitelisted audit covers1654 files across11 text/code/config extension classes: source/scripts/tests/docs/config/shell/notebooks plus selected allowed aggregate-run metadata and documentary provenance. Excluded data downloads/captures, restricted paths/families, entire paper and benchmarks directories from the completed pass. Output suppressed source values. No additional natality input or in-repository ACS 2010–2019 PUMS reader established. No-hit does not clear upstream frames or external sessions.

Evidence: `gates.yaml:1298`; `docs/baselines.md:555-557`; `docs/calibration-targets.md:45-62`; `docs/public-validation-inventory.md:34,57,75,147`.

**NCHS transitive provenance consumers.** CBO 2026 and TR2026 provenance call common2026 shared_files_sha256; this hashes NCHS even when CBO fertility uses its own rates. Declarative gate anchor and baseline documentation also name the2024 input.

Evidence: `src/populace_dynamics/baselines/cbo2026_long_term.py:330`; `src/populace_dynamics/baselines/tr2026_intermediate.py:245`; `src/populace_dynamics/baselines/common2026.py:25,97,113`; `gates.yaml:1298`; `docs/baselines.md:555-557`.

**Historical immigration schedule.** Progress records report a 2026-09-06 report-only entrant schedule with captured/hash-pinned Trustees immigration table and certified-frame donor feasibility check. Missing current native readers do not establish source nonuse; historical control cells/year ranges are unresolved without further cleared provenance. No run values opened.

Evidence: `docs/progress.md:331`; `docs/progress/progress.json:115`.

**Unspecified upstream frame ACS.** Microcosm documentation names ACS among source surveys without years/estimands. Independent2010–2019 exposure cannot be established solely by no current reader; coordinator must review upstream frame provenance.

Evidence: `docs/infrastructure.md:104-106`; `docs/methodology.md:9-11`; `docs/funder-summary.md:174-175`.

**ASFR callback and provenance consumers.** Baseline fertility step consumes the supplied ASFR callback; TrackA construction requests baseline provenance and therefore shared NCHS identity hashes. The global baseline selector still defaults toTR2008: the NCHS2024 shape default specifically belongs toTR2026Intermediate.

Evidence: `src/populace_dynamics/baselines/fertility.py:169-174`; `src/populace_dynamics/baselines/track_a.py:286-287`; `src/populace_dynamics/baselines/__init__.py:72-76`.

### Candidate unused natality observations

| Candidate | Evidence for repository nonuse | Remaining limit |
| --- | --- | --- |
| 2015 age-group natality | Outside fetcher annual2016–2024 range and committed JSON keys; no second natality reader established. | Coordinator confirms external/other-lane nonuse and J-first registry review. |
| Share male | SEX/IMP_SEX absent from committed ASFR extraction and its consumers. | Pin sex ratio on disjoint data; otherwise the validation estimand is consumed. |
| Mother’s nativity | MBSTATE_REC absent from ASFR selection; public2015 codebook documents it. | Bridge birthplace to ACS nativity; territories/citizenship-abroad differ. |
| Observed single maternal age | MAGER absent from committed grouped extraction; baseline single-age shape is interpolation, not these observations. | Confirm outcome nonuse; derived2024 shape remains exposed; freeze endpoint/denominator bridge. |

## Donor pools from documentation

The Microcosm start documents its frame at `docs/plans/microcosm-start.md:109–123`; this audit inspects no frame. ACS annual dictionaries and ReadMe document potential packet fields, not sufficient recent-arrival support. A current household is not necessarily an original immigration party.

| Packet need | Documented Microcosm frame | ACS PUMS documentation / implication |
| --- | --- | --- |
| Age/sex/nativity/citizenship/entry year | Present, with age topcodes and PEINUSYR entry-year representation. | AGEP/SEX/NATIVITY/CIT/POBP/YOEP; recent single-year entry coding. Reconcile concepts and precision. |
| Household/spouse/parent/arrival links | Marital/spouse links documented; no promise of intact entry parties. | SERIALNO/SPORDER and RELP, changing to RELSHIPP2019. Only identified relationships reconstructed; unknown stays unknown. |
| Earnings/work/disability | Primary frame documents earnings/work/disability; dense build omits some named items. | ESR/WAGP/SEMP/PINCP and disability items; neither observes legal status or statutory blindness. Packet mapping required. |
| Education and later mortality inputs | No educational attainment documented at line121. | SCHL documented. Adding mortality-lane education/race/earnings-rank requirements is separately scoped by design§3.6. |
| Parity | No documented children-ever-born seed guarantee. | Own children is not total parity; CPS June2012 PESF1 is a proposed bridge with household-age/date limits. |
| Weights/power | Frame design and recent-arrival donor counts not inspected. | Annual person/household80-replicate design documented; full ACS sample sizes do not establish recent-arrival PUMS critical-cell power. |

## Access table

Read dates refer to documentation/catalogs. **No linked data file was downloaded or opened.** Public-source status does not establish a separate file licence. Exact file-specific terms and captured bytes remain for the coordinator’s capture step. The complete official-page ledger, including unsuccessful attempts and incidental snippet URLs, appears in the companion report and the JSON `official_pages`/`audit_exceptions` fields.

| Source | URL / documentation | Licence or terms | Public | Documentation/date | Data-file reachability and reason |
| --- | --- | --- | --- | --- | --- |
| nchs: NCHS NVSS natality | [https://www.cdc.gov/nchs/data_access/vitalstatsonline.htm](https://www.cdc.gov/nchs/data_access/vitalstatsonline.htm) / [documentation](https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Dataset_Documentation/DVS/natality/UserGuide2015.pdf) | Public-use release under NCHS release policy; applicable file terms must be pinned at capture. | True | confirmed / 2026-10-24 | unverified: Only catalog, codebook and release policy read; no data file requested. |
| acs: ACS annual 1-year PUMS | [https://www.census.gov/programs-surveys/acs/microdata/documentation.html](https://www.census.gov/programs-surveys/acs/microdata/documentation.html) / [documentation](https://www2.census.gov/programs-surveys/acs/tech_docs/pums/ACS2014_PUMS_README.pdf) | Public federal statistical release, free of charge; attribute Census. File-specific conditions remain to confirm. | True | confirmed / 2026-10-24 | unverified: Dictionaries and ReadMe confirmed; data files deliberately not requested. |
| oact: OACT TR2026 demographic assumptions | [https://www.ssa.gov/oact/tr/2026/lrIndex.html](https://www.ssa.gov/oact/tr/2026/lrIndex.html) / [documentation](https://www.ssa.gov/oact/Downloadables/CY/index.html) | Public official catalog; separate dataset licence not established. | True | confirmed / 2026-10-24 | unverified: Catalog readable through web tool; ordinary HTTP request returned 403. No data table/file opened. |
| census2020: 2020 Census and 2020 coverage measurement | [https://www.census.gov/data/tables/2023/dec/2020-census-dhc.html](https://www.census.gov/data/tables/2023/dec/2020-census-dhc.html) / [documentation](https://www.census.gov/programs-surveys/decennial-census/about/coverage-measurement/similarities-differences-da-pes.html) | Public federal statistical release; attribute Census. Product-specific conditions remain to confirm. | True | confirmed / 2026-10-24 | unverified: Coverage documentation read; census and coverage data tables not opened. |
| census2023: Census 2023 national population projections | [https://www.census.gov/data/tables/2023/demo/popproj/2023-summary-tables.html](https://www.census.gov/data/tables/2023/demo/popproj/2023-summary-tables.html) / [documentation](https://www2.census.gov/programs-surveys/popproj/technical-documentation/methodology/methodstatement23.pdf) | Public federal statistical release; attribute Census. File-specific conditions remain to confirm. | True | confirmed / 2026-10-24 | unverified: Methodology and table catalog read; no projection data file requested. |
| cbo: CBO demographic projections | [https://www.cbo.gov/publication/61879](https://www.cbo.gov/publication/61879) / [documentation](https://www.cbo.gov/recurring-data/57059) | Public official release; separate dataset licence not established. | True | confirmed / 2026-10-24 | unverified: Landing pages and report documentation read; no workbook or CSV requested. |
| cps_fertility: CPS June Fertility Supplement | [https://www.census.gov/programs-surveys/cps/technical-documentation/complete/2012.html](https://www.census.gov/programs-surveys/cps/technical-documentation/complete/2012.html) / [documentation](https://www2.census.gov/programs-surveys/cps/techdocs/cpsjun12.pdf) | Public federal survey proposed as parity-seed source; release-specific terms not checked. | True | confirmed / 2026-10-24 | unverified: June 2012 and 2014 catalogs/codebooks confirmed; data files not requested. Fitting release still a proposal. |
| popest: Census resident population estimates | [https://www.census.gov/data/developers/data-sets/popest-popproj/popest/popest-vars.Vintage_2013.html](https://www.census.gov/data/developers/data-sets/popest-popproj/popest/popest-vars.Vintage_2013.html) / [documentation](https://www2.census.gov/programs-surveys/popest/technical-documentation/methodology/2010-2013/2013-natstcopr-meth.pdf) | Public federal statistical source; release-specific terms not checked. | True | confirmed / 2026-10-24 | unverified: Vintage 2013 resident-population methodology and DATE metadata confirmed; no estimates data requested. |

## Proposed conventions and remaining decisions

| Choice | Status | Recommendation | Authority |
| --- | --- | --- | --- |
| Exit timing and entry-year emigration | proposal_for_Max_or_coordinator | Draw deaths first; emigration among survivors in mortality slot before aging. Specify incumbent annual and entrant component-specific partial exposure. Do not declare universal entry-year exclusion or inclusion until component stayer controls reconcile without duplicate survival filtering. | 5c82dbd9:docs/design/open_population.md:350-357; src/populace_dynamics/engine/entrant_schedule.py:14-22,359-371 |
| OP5 reference date and annual collection mapping | proposal_for_Max_or_coordinator | July 1, 2013 reference with explicit ACS Jan–Dec collection-age/exposure bridge and uncertainty. The period release is not itself a July 1 snapshot. Freeze April 1 census and 2019 calendar-year mappings separately. | 5c82dbd9:docs/design/open_population.md:162,164,356-359; ACS period-estimates documentation |
| Group quarters and links | proposal_for_Max_or_coordinator | Keep institutional/noninstitutional GQ mass as separate strata; household packet/link rules apply only where observed relationships determine links. Publish unknown-link coverage. No inferred links from age/sex alone. | 5c82dbd9:docs/design/open_population.md:162,356; Census GQ documentation |
| gate_pop arms | proposal_for_Max_or_coordinator | Review feasibility of a primary fitted-law arm with genuinely2013-vintage assumptions; realized aggregate-control arm separate and conditional on those controls. Freeze arm choice/vintages before outcomes; if only realized arm feasible, narrow admission to composition. | 5c82dbd9:docs/design/open_population.md:164,358 |
| Mortality ownership | settled_by_approved_ruling_d1922 | Mortality lane SM owns death alignment; record OACT q as its target. OP6 consumes mortality and selects no deaths. | 5c82dbd9:docs/design/open_population.md:424-435 |

- Reserve J candidates first and add reviewed source/family vocabulary; resolve all underlying-data overlaps and merged hash at freeze.
- Ratify source-class numerical allowances, critical cells, zero-cell rule, pooling ladders and >=0.90 operating-characteristic alternatives after blinded feasibility review.
- Choose entry-year exit/timing, OP5 reference/GQ/date bridges and gate_pop arms; no provisional choice freezes itself.
- Confirm unused NCHS 2015/sex/nativity/observed-single-age targets and exact birth sex-ratio fitting partition; resolve ACS 2014/2019 upstream dependencies.
- Pin target bytes/row/column/vintage/terms through an authorized capture lane; settle unavailable fertility/CBO nativity margins and mortality interface.
- Locate matched recent-arrival cell-size/design documentation or authorize blinded counts later; no power conclusion is possible from overall ACS sample sizes.

## Audit limits and restricted-files statement

No microdata was opened and no real-data statistic or power calculation was computed. The NCHS input was inspected only through keys/provenance/hash; candidate16 run inspection selected only age/parity/cohort support metadata. No downloaded file was saved in the repository. This audit does not certify off-repository nonexposure, captured target bytes, sufficient cell sizes, numerical tolerances or source-specific terms.

No restricted local file, issue113, PR554 body, TrackB B0.2/successor working folder, U2 step4 run2 output, other session transcript/scratchpad or other Subfleet job folder was opened. On #560’s branch, only the two registry JSON files, `holdout_registry.py`, `tests/test_track_b_holdout_registry.py` and `tests/test_track_b_holdout_registry_committed.py` at `daf02425` were read. No artifacts named in those files were opened.

A subagent code-only search incidentally displayed hardcoded published NCHS TFR constants from scripts/fetch_nchs_asfr.py:119, tests/test_nchs_asfr.py:46, baselines/asfr.py:22,124. Parent received value-free disclosure only; no values retained here. No restricted local file or data table was opened.

An official SSA fertility-publication search returned cost/income/balance-section snippets. The subagent opened no such page/table/PDF, stopped general SSA search, and used only safe exact catalogs thereafter. Parent received value-free disclosure only. This prevents an unqualified no-restricted-text-exposure statement.

- https://www.ssa.gov/OACT/TR/2026/IV_B_LRest.html
- https://www.ssa.gov/oact/TR/2026/VI_D_LRsens.html
- https://www.ssa.gov/oact/TR/2024/IV_B_LRest.html
- https://www.ssa.gov/OACT/TR/2024/IV_B_LRest.html
- https://www.ssa.gov/oact/TR/2025/IV_B_LRest.html

An initial filename whitelist included paper/paper.qmd, which the restrictions list separately labels cleared at an earlier commit. The subagent interrupted that value-suppressed scan; it cannot establish whether that path was reached, and no paper content/value was displayed. The completed broad scan excluded paper/ and benchmarks/ entirely. No standing restricted-list path was included in either whitelist.

These incidents are disclosed without their values. No claim of completely unexposed source discovery is made. A coordinator must decide their implications for later blinded roles; this lane makes no methodology ruling.

## Verification and handoff

The documentation-only unit test validates six complete draft records, pending held-out years, registry commit/hash, target manifests and unrun named power procedures. It imports no model code and reads only `docs/design/`. Run `.venv/bin/python -m pytest -q -m unit tests/open_population/test_op0_1_records.py`; Black79 and Ruff apply to that test. Tier count files remain untouched as instructed; their repository-wide policy count is deliberately deferred to the coordinator.

See [the report](open_population_op0_1_report.md) for commit IDs, test results and the official-page ledger.
