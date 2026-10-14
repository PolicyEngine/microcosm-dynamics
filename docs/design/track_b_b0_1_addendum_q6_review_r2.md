REQUEST CHANGES

**High:** None. No prohibited statistic or outcome was encountered.

**Medium**

- **The registered resampling rule permits a non–Rao–Wu fallback.** `docs/design/track_b_b0_1_addendum.md:303` imports the ordinary bootstrap branch at `scripts/track_b_b0_1_planning_values.py:986` for strata with three or more clusters. The addendum acknowledges its variance understatement, but permits it despite d782’s Rao–Wu ruling (`_review_context/d782-ruling.md:5`). This can make B2’s bounds too narrow. **Smallest fix:** require B2’s scorer to reject such strata before candidate runs. Preserve the pinned planning script and protocol; test the rejection with invented inputs. The current two-cluster planning record is unaffected.

- **M3’s output accounting misses revision-prefixed Git results.** `scripts/track_b_b0_1_addendum_reads.py:385` splits at the first colon. An invented excluded-path line counts as one; the same line prefixed by `HEAD:` counts as zero. Recorded calls use `git grep … HEAD` at `docs/design/track_b_b0_1_addendum_reads.json:850`, `:859` and `:864`. Their zero counts cannot establish that no excluded filenames appeared, so section 14’s breakdown remains insufficiently supported (`docs/design/track_b_b0_1_addendum.md:1117`). **Smallest fix:** recognize revision-prefixed output, add regression coverage, regenerate from the existing export, and restate the affected classifications. This establishes an accounting defect, not an observed blindness breach.

- **The Codex logger can approve an escaping shell-variable path.** `scripts/track_b_b0_1_review_root.py:408` resolves variables literally. An in-memory transcript containing a `$PWD` path followed by a parent traversal returns `review_counts=True`, although shell expansion would leave the root. This defeats the logger’s stated rule at `:368`. **Smallest fix:** resolve supported variables against the lane’s known environment or reject unresolved path variables, with a regression test. No escaping command was executed during this review.

**Low**

- **The scope count is wrong.** `docs/design/track_b_b0_1_addendum.md:1275` says thirteen scope-flagged calls. The record contains fourteen: three author calls and eleven agent calls. **Smallest fix:** change “Thirteen” to “Fourteen” and pin this total in the record test.

- **The review description still describes round 1’s context and lane.** `docs/design/track_b_b0_1_addendum.md:1205` names five context copies, and `:1210` specifies the Opus tool lane. This root has nine context copies; the tool now supports Codex logs. **Smallest fix:** describe the round-2 additions and Codex format explicitly. The user’s instructions authorize this review’s shell commands.

- **The new-root handoff lacks an executable interface.** `docs/design/track_b_b0_1_addendum.md:1022` says the scorer passes its root, but the imported functions accept no root argument (`scripts/track_b_b0_1_planning_values.py:926`, `:966`) and use the module constant (`:976`). A literal implementation could use the planning root instead of B2’s registered root. **Smallest fix:** specify how the scorer initializes that constant, including spawned workers, or supplies an adapter, without changing the pinned planning script.

**Answers to the seven questions**

**1. Round 1**

| Finding | Assessment |
|---|---|
| M1 | Resolved: the flip is corrected and option (d) includes tolerance/scoring alternatives and costs. `docs/design/track_b_b0_1_addendum.md:648`, `:923`. |
| M2 | Resolved in substance: sampling uncertainty is disclosed and the design-df t rider is registered. `docs/design/track_b_b0_1_addendum.md:574`, `:319`, `:330`. |
| M3 | Partly resolved. Recursive/glob scopes are flagged and full commands retained, but revision-prefixed output is missed. `scripts/track_b_b0_1_addendum_reads.py:323`, `:381`; medium finding above. |
| L1 | Resolved: the audit now qualifies these figures as reference points. `docs/design/track_b_b0_1_audit.md:98`, `:817`, `:1006`. |
| L2 | Resolved outside the preserved protocol: nominal tolerances and sensitivity results are explicit. `docs/design/track_b_b0_1_addendum.md:595`, `:655`. |
| L3 | Resolved: constants are distinguished from the actual blindness evidence. `docs/design/track_b_b0_1_addendum.md:467`. |
| L4 | Seeds are now named. The separate interface issue remains above. `docs/design/track_b_b0_1_addendum.md:350`. |
| L5 | Resolved as far as this root permits: command, time and script state are supplied. `docs/design/track_b_b0_1_addendum.md:899`. |
| L6 | Resolved by the explicit 2.34 correction. `docs/design/track_b_b0_1_addendum.md:658`. |
| L7 | Resolved by the requested disclosure of the worker-refusal behavior. `docs/design/track_b_b0_1_addendum.md:475`. |

Section 14 accurately restates the current record’s classifications and counts, but those classifications do not reliably establish the actual Git output until the counter is fixed. The record retains every flagged command; its command hashes agree.

**2. Fidelity to the rulings**

The three ruling quotations match their context copies, and the six-cell scope, report-only cells, downstream limitations and household splits are carried accurately (`docs/design/track_b_b0_1_addendum.md:111`, `:188`, `:308`, `:1027`). The ≥3-cluster fallback prevents complete fidelity to d782.

The M2 rider is consistent across the uncertainty rule, pass rule and floor-builder inputs (`docs/design/track_b_b0_1_addendum.md:330`, `:375`, `:415`). B2 uses its counted ν; 63 is the planning evaluation’s value.

**3. Completeness**

All ten elements and the named procedure are present (`docs/design/track_b_b0_1_addendum.md:143`). Numerical tolerances and final retained cells follow frozen rules applied to B2’s floor. No post-outcome rerun, seed change, tolerance change or rescoping is permitted (`:392`).

The record still needs the resampling guard and handoff clarification above. d1342 and the required B1 pass remain registration preconditions; the open decision is correctly distinguished from an addendum-merge precondition (`:866`, `:888`).

**4. The ruled power**

Yes: section 11 follows the record and applies section 16’s verdict correctly. Six-cell binding power is 0.813, while a four-cell surface retaining both families reaches 0.964; therefore the protocol verdict is feasible subject to B2’s floor (`docs/design/track_b_b0_1_addendum.md:728`, `:752`).

The separate hold for Max is stated accurately: d781 rested on the household-basis 0.952 figure (`:809`, `:877`). The figures and rendered tables agree with the records; the prose pins cover the new figures (`tests/test_track_b_b0_1_addendum_record.py:632`).

**5. Statistics**

The two-cluster multiplicities are correct. The ≥3-cluster branch is not Rao–Wu. Keeping a singleton fixed gives zero variance contribution and requires a certainty-PSU justification or explicit handling of noncertainty singletons (`scripts/track_b_b0_1_planning_values.py:981`).

Keeping household se_up and household seed spread is consistent with the registered units and splits (`docs/design/track_b_b0_1_addendum.md:309`, `:717`). Σ(n_h−1) is conventional nominal design df; applying its t value to the whole se_c is conservative under the stated fixed-added-variance model (`:319`, `:325`).

The ruled-power implementation correctly separates `(rd)²`, the random estimated sampling variance, and the registered estimation component (`scripts/track_b_b0_1_ruled_power.py:37`, `:372`). Its Gaussian/chi-square independence assumptions remain model assumptions; the tests validate implementation of that model.

**6. Consistency**

The records, tables and current verdict agree, subject to the findings above. Read-only checks passed for both power records’ planning-input hashes, the planning-script hash, all nine rendered tables/verdict text, and the ruling pins.

The section-16 block matches the unchanged pinned SHA-256, beginning `2a1681cdb3b6e28f` (`tests/test_track_b_b0_1_addendum_record.py:54`; `scripts/track_b_b0_1_planning_values.py:108`).

**7. Exposure**

The stored accounting and round-1 read-log totals are internally consistent. Sections 14–15 need the output-counter correction, fourteen-call correction and round-2 description update. The second session’s claimed reads cannot be independently verified from its prose alone (`docs/design/track_b_b0_1_addendum.md:1154`).

Nothing opened during this review exposed a B2 outcome or a selector outcome at pseudo-boundary 2008/2010.

**Could not check inside the root**

- Original transcript exports and actual revision-prefixed Git output.
- The second authoring session’s complete transcript.
- Excluded files, external source data, and historical source bytes.
- Git history proving freeze timing and the claimed historical changes.
- The independent power reviews and mutation logs cited by `_review_context/OPTIONS.md:129`.
- B2’s eventual strata, floor and implemented scorer.
- Full numerical reproduction or CI execution. This review used source inspection and limited standard-library checks without creating artifacts.

**Read log**

All paths are relative to the root. This includes delegated review work.

Opened or content-searched:

```text
_review_context/OPTIONS.md
_review_context/d622-ruling.md
_review_context/d693-RECOMMENDATION.md
_review_context/d693-ruling.md
_review_context/d765-ruling.md
_review_context/d781-ruling.md
_review_context/d782-ruling.md
_review_context/trackb-design-20260928.md
docs/design/track_b_b0_1_addendum.md
docs/design/track_b_b0_1_addendum_power.json
docs/design/track_b_b0_1_addendum_q6_readlog_r1.json
docs/design/track_b_b0_1_addendum_q6_review_r1.md
docs/design/track_b_b0_1_addendum_q6_root_r1.json
docs/design/track_b_b0_1_addendum_reads.json
docs/design/track_b_b0_1_audit.md
docs/design/track_b_b0_1_exposure_inventory.json
docs/design/track_b_b0_1_exposure_inventory_addendum.json
docs/design/track_b_b0_1_exposure_inventory_r2.json
docs/design/track_b_b0_1_planning_values.json
docs/design/track_b_b0_1_ruled_power.json
scripts/track_b_b0_1_addendum_power.py
scripts/track_b_b0_1_addendum_reads.py
scripts/track_b_b0_1_addendum_tables.py
scripts/track_b_b0_1_counts.py
scripts/track_b_b0_1_planning_values.py
scripts/track_b_b0_1_review_root.py
scripts/track_b_b0_1_ruled_power.py
tests/test_track_b_b0_1_addendum_reads.py
tests/test_track_b_b0_1_addendum_record.py
tests/test_track_b_b0_1_review_root.py
tests/test_track_b_b0_1_revision1_tools.py
tests/test_track_b_b0_1_ruled_power.py
```

Additional filenames returned by filename-only searches; their contents were not opened:

```text
_review_context/pr490-comments.md
docs/literature-review.md
docs/design/anchor_context_extraction.md
docs/design/assembled-history-observer.md
docs/design/boomers2004_1946_55_comparison.md
docs/design/boomers2004_uniform_cut_comparison.md
docs/design/closed-cohort-history.md
docs/design/cola-age-profile-tabulation.md
docs/design/compact-cohort-history.md
docs/design/covered-wage-history.md
docs/design/di_entitlement.md
docs/design/e4_e5_audit_manifest.md
docs/design/first_estimates_report.md
docs/design/forward-earnings-history.md
docs/design/gate_epuf_block_draft.yaml
docs/design/gate_m6_block_draft.yaml
docs/design/m6_candidate2_activation_notes.md
docs/design/m6_candidate2_decision9_readjudication.md
docs/design/m6_remarriage_learning_plan_round2.md
docs/design/m6_remarriage_learning_plan_round2_validation.json
docs/design/m6_remarriage_round3_amendment.md
docs/design/m6_remarriage_round4_amendment.md
docs/design/m6_remarriage_round5_amendment.md
docs/design/m6_remarriage_round6_amendment.md
docs/design/m6_remarriage_surface_question.md
docs/design/minimum_benefits_comparison.md
docs/design/mortality-observer.md
docs/design/pe_us_bridge.md
docs/design/pe_us_depletion_cut.md
docs/design/pe_us_population_run.md
docs/design/person-identity-map.md
docs/design/psid2010-cohort.md
docs/design/track-a-assembly.md
docs/design/track_b_b0_1_counts.json
docs/design/track_b_b0_1_gate_leak_check.txt
docs/design/track_b_b1_registration_draft.md
docs/design/track_b_b1_v2_amendment.md
docs/design/track_b_g_gross_benefits.md
docs/design/u2_m1_captured_sources.md
docs/design/u2_m1_exposure.json
docs/design/u2_m1_exposure.md
docs/design/u2_m1_income_wealth_adjudication.md
docs/design/u2_m1_income_wealth_exposure.json
docs/design/u2_m1_pension_adjudication.md
docs/design/u2_m1_pension_exposure.json
docs/design/u2_m1_report.md
docs/design/u2_m1_root_exposure.json
docs/design/u2_m1_runtime_exposure.json
docs/design/u2_m1_source_adjudication.md
docs/design/u2_m1_ssi_adjudication.md
docs/design/u2_m1_ssi_exposure.json
docs/design/u2_m1b_exposure.md
docs/design/u2_m1b_psid_research.md
docs/design/u2_m2_exposure.json
docs/design/u2_m2_exposure.md
docs/design/u2_m2_report.md
docs/design/u2_m2_u1_differential_12e1db0.json
docs/design/u2_m2_u1_differential_f16f1b9.json
docs/design/urban2010_cola_comparison.md
docs/design/urban2010_fra68_comparison.md
docs/design/urban2010_track_a_v2.md
docs/design/urban2010_track_a_v2_implementation.md
docs/design/urban2010_track_a_v2_invariants.md
docs/design/urban2010_track_a_v2_reads.txt
docs/design/urban2010_track_a_v2_rulings.md
pyproject.toml
reviews/gate_epuf_round1_referee_20261002.md
reviews/gate_epuf_round3_rereview_20261002.md
scripts/track_b_b0_1_exposure_inventory.py
scripts/track_b_b0_1_gate_leak_check.py
scripts/track_b_b0_1_review_power.py
tests/conftest.py
tests/test_track_b_b0_1_addendum_power.py
tests/test_track_b_b0_1_audit_record.py
tests/test_track_b_b0_1_counts.py
tests/test_track_b_b0_1_planning_values.py
tests/track_u2/conftest.py
```

Filename searches included `AGENTS.md`; none matched.