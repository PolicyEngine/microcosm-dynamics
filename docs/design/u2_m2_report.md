# U2 milestone 2 report: implementation on invented data

**INVENTED DATA - NOT A COMPARISON.** Milestone 2 builds everything in specification §14's implementation table, and every §13 test, without running anything on real data. The specification is [`boomers2004_1946_55_comparison.md`](boomers2004_1946_55_comparison.md) (`u2-draft-4`, unratified). This report has five parts:

- the §13/§14 completeness audit;
- what the finishing lane built;
- the invariants and their tests;
- the test and differential evidence;
- the conservative readings and what remains.

The exposure record is [`u2_m2_exposure.md`](u2_m2_exposure.md).

- **Branch:** `dynamics-u2-m2-20260928`, rebased onto `b948d6b` (milestone 1b's fixed head, which includes milestone 1 and the applied source adjudication at `883ea48`).
- **Code-final commit:** `12e1db0`. Later commits change only `tests/tier_counts.json`, `tests/README-tiers.md` and `docs/design/` (this report, the exposure record and the differential's report).
- **Blindness:** no lane opened any file `RESTRICTED-FILES.md` restricts, and nothing here states or implies a 1946–55 value or direction. Every number in the code, tests and dry run is invented, a policy parameter or a committed public parameter capture.

## §13 and §14 completeness audit

Status is DONE with the evidence, or MISSING. Test references are `file::test` under `tests/track_u2/` unless a path is given. Nothing buildable on invented data is MISSING. The three MISSING rows are real-run outputs or an optional check that needs Max's approval.

### §13 required U2 tests

| §13 group | Status | Evidence |
|---|---|---|
| Observation plans: U0 five pairs; U1 fifteen pairs over ten births; multipliers sum to one per birth year | DONE | `test_u2_plans.py::test_u0_has_five_exact_age_pairs`, `::test_u1_has_fifteen_pairs_over_ten_births_summing_to_one`, `::test_plan_equals_the_milestone_1_support_registry` |
| Boundary wave: 2013 only for 1946 at 66 in U1 | DONE | `test_u2_plans.py::test_wave_2013_is_an_observation_only_for_1946_at_66`, `::test_design_frame_of_u1_includes_the_2013_wave` |
| Missing observations: no transfer or renormalization of a missing half weight | DONE | `test_u2_plans.py::test_missing_observation_keeps_its_half_weight` |
| Support separation: support-only waves never in U0's observations or design frame | DONE | `test_u2_plans.py::test_support_waves_never_enter_u0_observations_or_design` |
| Identification: shared observations have identical births and annuitant attributes | DONE | `test_u2_plans.py::test_shared_observations_have_identical_births_and_annuitants`, `::test_births_are_derived_once_and_refused_from_other_inputs`, `::test_seed_is_the_earliest_positive_weight_presence` |
| Cohort bounds: birth-year, age, income-year and wave relations; outside births excluded with dispositions | DONE | `test_u2_plans.py::test_cohort_bounds_and_outside_births`, `::test_dispositions_are_counted`, `::test_every_target_cell_is_observed_or_disposed_exactly_once` (new) |
| Labels: codes 10/20/22/88/90 in every support wave; 92 absent 2013/2015, present 2017–2023; birth-year anchor labels | DONE | `test_u2_roles.py::test_relationship_labels_carry_the_documented_prefixes` (the `PREFIXES` table), `::test_reported_birth_year_anchor_labels` |
| Roles: code 20 of either sex, 90, 92, 88, cohabitor slots, zero-weight legal spouses, unresolved/ambiguous pairings | DONE | `test_u2_roles.py::test_code_20_of_either_sex_occupies_the_spouse_slot`, `::test_code_90_is_ofum_income_and_a_legal_spouse_life`, `::test_code_92_is_ofum_never_a_legal_spouse_and_never_resolves`, `::test_administrative_birth_support_is_administrative_only`, `::test_code_88_refuses_under_every_context`, `::test_cohabitor_22_occupies_the_slot_without_legal_status`, `::test_zero_weight_legal_spouse_keeps_a_derived_age`, `::test_ambiguous_pairing_stays_unresolved_and_counted`, `::test_every_pairing_state_is_named`, `::test_registry_context_refuses_refused_codes` |
| Income/wealth maps: labels and widths, losses, sentinels, seven/eight-asset identities, debt once, home equity excluded | DONE | `test_u2_mappings.py::test_specs_carry_exact_registry_labels_positions_and_widths`, `::test_losses_top_codes_and_sentinels_are_carried`, `::test_wealth1_identity_seven_or_eight_assets_debt_once` (asserts `excluded == "home_equity"`), `::test_wealth1_identity_counts_a_broken_identity`, `::test_parse_refuses_undocumented_values`, `::test_registry_gate_refuses_every_open_wave` |
| Employer DC: routes, checkpoint branches, IRA rollovers, duplicate accounts | DONE | `test_u2_employer_dc.py`: 32 tests, including `::test_combined_previous_plan_counts_its_both_items_once`, `::test_rollover_into_an_ira_is_excluded_and_counted`, `::test_registry_documents_dc_only_checkpoints_from_2017`, `::test_later_wave_routes_refuse_under_the_registry_gate` |
| Design: strata 88–94, invalid design, zero-contribution clusters, singletons, paired change SE | DONE | `test_u2_design_floor.py::test_refresher_strata_88_to_94_are_valid`, `::test_invalid_design_refuses`, `::test_zero_contribution_clusters_enter_the_variance`, `::test_singleton_strata_are_excluded_counted_and_listed`, `::test_paired_change_se_uses_the_indicator_difference` |
| Floor: transitive linkage, both observations on one side, undefined floors, seed count | DONE | `test_u2_design_floor.py::test_split_units_link_family_units_transitively`, `::test_both_observations_of_a_person_fall_on_one_side`, `::test_undefined_floors_and_the_required_seed_count`, `::test_floor_is_not_rescaled_and_uses_sample_sd` |
| Parameters: complete years, 2022 precision, 2012 overlap, unknown revision, constants | DONE | `test_u2_parameters.py::test_threshold_coverage_includes_every_required_year`, `::test_2022_precision_is_read_as_captured`, `::test_2012_equals_u1_capture_in_every_entry`, `::test_unknown_revision_is_refused`, `::test_varying_constants_and_other_years_are_refused`, `::test_ssi_capture_years_revision_constants_and_2012` |
| Memo: small cells, no-switcher wording, undefined cells, rounding endpoints | DONE | `test_u2_memo.py::test_small_cells_are_flagged`, `::test_no_switcher_cell_reports_uncertainty_not_estimable`, `::test_undefined_cells_keep_their_reason`, `::test_exact_change_endpoint_is_on_the_edge` |
| Identity: wrong cohort, seed, column, rulings, parameters, provenance and artifact destination refuse | DONE | `test_u2_identity.py::test_u2_refuses_u1_identities` (column, statistic, specification, threshold and SSI hashes, seed rule, artifact and sidecar), `::test_u2_refuses_u1_rulings_and_max_rulings`, `::test_wrong_target_objects_refuse`; `test_u2_plans.py::test_cohort_spec_refuses_other_settings`, `::test_invented_provenance_is_checked`; `test_u2_scripts.py::test_preflight_refuses_before_the_specification` (output path) |
| Historical isolation: exact exclusions; transitive non-reachability | DONE | `test_u2_isolation.py::test_every_u2_module_is_an_exact_historical_exclusion`; `tests/estimates/test_birth_evidence_artifact.py::test_post_review_sources_are_outside_historical_reducer_identity` (exact tuple), `::test_post_review_exclusions_are_unreachable_from_birth_evidence` |

### §13 invariants and other required tests

| §13 requirement | Status | Evidence |
|---|---|---|
| Per observation, every row (U1, U3, U4 included) and each half-split: \(R_i\le B_i\), \(1(R_i<T_i)\ge1(B_i<T_i)\) | DONE | `test_u2_properties.py::test_reform_never_exceeds_baseline_in_any_row` (Hypothesis), `::test_per_observation_monotone_in_the_invented_run_and_every_half`, `::test_per_observation_monotone_in_every_half_of_every_split`; the dry run records it for all ten rows |
| \(0\le\) offset \(\le\) fall \(\le cS\); fall = 0 when \(S\le G\); offset ≤ FBR room | DONE | `test_u2_properties.py::test_countable_fall_bounds`, `::test_countable_income_falls_by_at_most_the_cut`, `::test_ssi_response_bounds_hold_on_the_estimator` (Hypothesis, cut drawn in [0, 1]) |
| New enrollment: \(0\le SSI_{new}\le\min(F-C',C-C')\) | DONE | `test_u2_properties.py::test_new_enrollment_bound_holds_and_binds` (Hypothesis, targeted strategy) |
| Zero-cut identity | DONE | `test_u2_properties.py::test_zero_cut_identity` |
| Poverty rates within [0, 100]; positive common weight-scaling invariance | DONE | `test_u2_properties.py::test_cells_and_halves_monotone_bounded_and_scale_invariant`; `::test_rate_bound_counterexample_is_a_one_ulp_rounding` records the minimized counterexample (one ulp above 100 from U1's inherited expression) |
| Rejection of malformed plans or missing parameters | DONE | `test_u2_properties.py::test_malformed_plans_are_rejected`, `::test_perturbed_plans_are_refused`, `::test_missing_threshold_years_are_rejected`; `test_u2_plans.py::test_malformed_plans_refuse`, `::test_malformed_inputs_refuse` |
| Mirror `test_nobody_leaves_poverty_under_the_cut` for the U2 artifact | DONE | `test_u2_pipeline.py::test_nobody_leaves_poverty_under_the_cut` (skips until the registered artifact exists), `::test_nobody_leaves_poverty_under_the_cut_invented` |
| Retain U1's worked cases (annuity prices, strict threshold, SSI caps and exclusions, new enrollment, farm losses, retirement-account removal, unresolved marital status, annuitant ages, employer DC) | DONE | `test_u2_worked_cases.py` (14 tests, re-worked by hand at income year 2014 and 3 percent); marital status, annuitant ages and DC routes in `test_u2_roles.py`, `test_u2_plans.py` and `test_u2_employer_dc.py` |
| U1 differential: entire canonical JSON and normalized Markdown, zero tolerance, seed 20260924, `9cee2423` against the candidate | DONE, executed | `scripts/u2_u1_differential.py`; `test_u2_differential.py` (8 tests); executed on 12e1db0, see "U1 differential evidence" |
| Contract check: `age67.WAVES` | DONE, executed | the harness's probe (`age67.WAVES`), equal at both commits |
| Contract check: `observation_plan` for U0, U1, U0-F | DONE, executed | probe `observation_plan` |
| Contract check: `pending_decisions()` of `age67`, `adjusted_poverty`, `uniform_cut_tabulation` | DONE, executed | probe `pending_decisions` |
| Contract check: `rows.MAX_RULINGS` | DONE, executed | probe `rows.MAX_RULINGS` |
| Contract check: `runner.NAMED_DELTAS` | DONE, executed | probe `runner.NAMED_DELTAS` |
| Contract check: `REPORT_ROWS` and `COMPARATOR_COLUMN` | DONE, executed | probe `uniform_cut_tabulation.REPORT_ROWS`, `…COMPARATOR_COLUMN` |
| Contract check: `input_frames_sha256()`, supplements staged and refused | DONE, executed | probe `input_frames_sha256` |
| Contract check: actual loader's frame and seal hashes with patched readers, refused supplements and refused file access | DONE, executed | probe `actual_loader`; `test_u2_differential.py::test_the_loader_guard_records_every_access_under_the_fake_root`; every access list empty |
| Refusal parity: invalid provenance | DONE, executed | harness `EXPECTED_REFUSALS["invalid_provenance"]`, met at both commits |
| Refusal parity: invented run with a pointer | DONE, executed | `invented_with_pointer` |
| Refusal parity: invalid registration URL | DONE, executed | `invalid_registration_url` |
| Refusal parity: invented inputs labelled registered | DONE, executed | `invented_labeled_registered` |
| Refusal parity: wrong registered headline | DONE, executed | `wrong_registered_headline` |
| Refusal parity: wrong threshold hash | DONE, executed | `wrong_threshold_hash` |
| Refusal parity: wrong SSI hash | DONE, executed | `wrong_ssi_hash` |
| Refusal parity: existing artifact | DONE, executed | `existing_artifact` (the fixed one-shot message) |
| Refusal parity: existing sidecar | DONE, executed | `existing_sidecar` (the artifact-named message) |
| Refusal parity: U2 seed under U1 | DONE, executed | `u2_seed_under_u1`; also `test_u2_identity.py::test_u2_seed_refusal_message_is_u1s_unchanged` |
| Existing U1 suite unmodified and passing | DONE | `git diff 9cee2423` over the §13 list is empty; all pass or skip (below) |
| U1 specification, captures, registered artifact and sidecar unchanged | DONE | `test_u2_isolation.py::test_no_committed_run_engine_gate_or_u1_file_changed`, `::test_protected_bytes_match_the_milestone_1_manifest` |
| Optional structure-only U1 load (pin `43c41f44…`) | MISSING (optional; needs Max's explicit OK; §13) | not run |

### §14 implementation table

| §14 area | Status | Evidence |
|---|---|---|
| Cohort configuration: U2 support/observation plans and identity; U1 API and defaults preserved | DONE | `uniform_cut_track_u2/cohort.py` (`U2CohortSpec` :199, `plan_cells` :253, `check_plan_against_support_registry` :310); `test_u2_plans.py::test_u1_plan_does_not_alter_u1_of_track_u`, `test_u2_isolation.py::test_u1_wave_pins_and_shared_constants_are_unchanged` |
| Birth-year law: call `career.py:642`, no edit | DONE | `cohort.py:706` and `:760` call `career.derive_birth_years` (`career.py:642`); `career.py` unchanged against `9cee2423` |
| Income and DC mappings: adjudicated registries and adapters; U1 registries preserved | DONE | `sources.py` (registry and declared gates, `field_specs`, `dc_route`), `loader.py`; `test_u2_mappings.py`, `test_u2_employer_dc.py`, `test_u2_loader.py`; every TO VERIFY or refused route refuses (`::test_registry_gate_refuses_every_open_wave`, `::test_registry_gate_agrees_with_the_loader_api`, `test_u2_roles.py::test_role_refusals_agree_with_the_loader_api`) |
| `data/family.py`, `data/psid.py`, `estimates/career.py` read-only | DONE | `git diff 9cee2423` empty; `test_u2_isolation.py::test_no_committed_run_engine_gate_or_u1_file_changed` |
| Income estimator: explicit U2 parameter and role context; U1 pins and IRA-year behavior preserved | DONE | `estimator.py` (`U2IncomeSpec` :83, `U2EstimatorContext` :144, `u2_adjusted_incomes` :265); `test_u2_estimator.py::test_u2_estimator_equals_u1_on_rows_both_accept`, `::test_head_ira_income_is_removed_in_every_u2_income_year`, `::test_context_and_target_guards`, `::test_u1_captures_refused_by_the_estimator`; `adjusted_poverty.py` unchanged |
| Threshold access: the full registered capture (Track M's) | DONE | `parameters.py::load_u2_thresholds` (:146); `test_u2_parameters.py::test_threshold_capture_is_the_pinned_track_m_file`, `::test_threshold_coverage_includes_every_required_year` |
| Tabulation identity separate from U1's `COMPARATOR_COLUMN` | DONE | `tabulation.py`, `identity.py`; `test_u2_identity.py::test_u2_identity_is_separate` |
| Runner: separate rows, literal deltas, rulings, fixed headline | DONE | `rows.py`, `runner.py`; `test_u2_identity.py::test_named_deltas_equal_section_12_literally`, `::test_rows_equal_the_section_15_block`, `::test_fixed_headline_refuses_fallback`, `::test_draft_block_rulings_are_refused_until_materialized`; `test_u2_pipeline.py::test_every_row_is_computed_with_the_u2_identity` |
| Capture configuration: separate U2 SSI years and output | DONE (milestone 1) | `scripts/capture_track_u2_ssi_parameters.py`; `test_ssi_capture.py` (31 tests) |
| Invented dry run `scripts/track_u2_dry_run.py` | DONE, executed | `test_u2_scripts.py::test_every_dry_run_output_is_headed_invented`, `::test_dry_run_records_every_branch_and_refusal`, `::test_dry_run_markdown_names_the_refusals`; run at 12e1db0 (below) |
| Structural and component entry points, no poverty import | DONE | `scripts/track_u2_structure.py`, `scripts/track_u2_component_diagnostics.py`; `test_u2_scripts.py::test_pre_registration_scripts_cannot_reach_the_poverty_computation`, `::test_pre_registration_scripts_refuse_before_opening_psid` |
| Registered entry point `scripts/run_track_u2_registered.py` | DONE (built; refuses at the adjudicated registries) | `preflight` (:207); preflight tests below |
| Artifact `runs/replication_boomers2004_1946_55_v1.json` | Identity DONE; artifact MISSING (only the authorized registered run produces it) | `identity.ARTIFACT_PATH`; `test_u2_identity.py::test_u2_identity_is_separate` |
| Environment sidecar `…_v1.env.json` | Identity DONE; sidecar MISSING (as above) | `identity.SIDECAR_PATH`; the same test |
| Historical source protection: every new module in `POST_REVIEW_SOURCE_EXCLUSIONS`, the exact tuple and the reachability tests | DONE | `scripts/first_estimates_birth_evidence.py` lists all 13 package modules and 5 U2 scripts, including `u2_u1_differential.py`; `tests/estimates/test_birth_evidence_artifact.py` (13 passed): `::test_reducer_input_identity_matches_reviewed_branch`, the exact tuple and transitive reachability tests |
| Wave isolation: U1's waves pinned; no shared `INCOME_WAVES` extension | DONE | `test_u2_isolation.py::test_u1_wave_pins_and_shared_constants_are_unchanged`; differential `age67.WAVES` equal |
| Dry run exercises all ten rows, mapping and role branches, refusals, rejection by the registered runner | DONE, executed | the RESULTS.md "Checks" section: ten rows, six mapping round trips, 8 named variants, 9 cross-cohort refusals, the registered guard's refusal |

### §14 cross-cohort refusals

| §14 refusal | Status | Evidence |
|---|---|---|
| U1's loaders and runner refuse the Track M threshold capture and any U2 SSI capture | DONE | `test_u2_parameters.py::test_u1_runner_refuses_the_track_m_and_u2_captures` (U1 runner `_check_parameters`, and `ap.load_poverty_thresholds` / `ap.load_ssi_parameters` refuse the files) |
| U2 refuses U1's threshold `dc21a787…` and SSI `79e641a1…` | DONE | `test_u2_parameters.py::test_u1_captures_are_refused_as_u2_sources`; `test_u2_identity.py::test_u2_refuses_u1_identities` |
| U1's `Age67Spec` refuses U2 settings; U2's configuration refuses U1 identities and seeds | DONE | `test_u2_identity.py::test_u1_guards_refuse_u2_seed_and_rows`; `test_u2_plans.py::test_cohort_spec_refuses_other_settings` |
| U2 refuses U1's specification, column, rows/rulings, `MAX_RULINGS` and artifact path | DONE | `test_u2_identity.py::test_u2_refuses_the_u1_specification_block`, `::test_u2_refuses_u1_identities`, `::test_u2_refuses_u1_rulings_and_max_rulings` |
| U2 has its own rulings record | DONE | `rows.U2_RULINGS`; `test_u2_identity.py::test_draft_block_rulings_are_refused_until_materialized` |
| Caller-supplied expected hashes cannot bypass the parameter bundle | DONE | `test_u2_parameters.py::test_loaders_take_no_caller_supplied_hash`, `::test_registered_check_needs_every_u2_pin` |

### §14 registered-run preflight

| §14 preflight item | Status | Evidence |
|---|---|---|
| Ratified specification, completed decisions, empty blockers | DONE | `run_track_u2_registered.py::check_specification_ratified`; `test_u2_scripts.py::test_preflight_refuses_the_draft_specification`, `::test_preflight_refuses_incomplete_specifications` |
| Exact registered commit and clean checkout | DONE | `test_u2_scripts.py::test_preflight_refuses_before_the_specification` (short SHA, other HEAD, dirty tree) |
| Registration binding: target, specification hash, rows, plans, maps, source identities, parameter pins | DONE | `registration_binding`, `binding_sha256`; `test_u2_scripts.py::test_binding_covers_every_registered_identity`, `::test_preflight_refuses_a_wrong_binding_then_the_open_mapping`, `::test_preflight_refuses_a_plan_the_support_registry_does_not_hold` |
| Fixed U0 headline and exact output identity | DONE | `test_u2_scripts.py::test_registered_headline_choice_is_only_u0`, `::test_preflight_refuses_before_the_specification` (U1 artifact, other path) |
| Nonexisting artifact and sidecar | DONE | `test_u2_scripts.py::test_existing_artifact_or_sidecar_refuses` |
| Complete parameter coverage including 2012 | DONE | `parameters.check_u2_parameters` in the preflight; `test_u2_parameters.py::test_registered_check_needs_every_u2_pin`, `::test_threshold_coverage_includes_every_required_year` |
| Completed independent mapping review and pre-registration evidence | DONE (conservative reading 5) | `loader.source_preflight` refuses while any applied entry is TO VERIFY or blocked; the block's `blocked_by` names `mapping_manifests_and_independent_review` and `preregistration_structure_reconciliation_and_f17_pass`, and the preflight refuses a nonempty `blocked_by` |
| Target identity through loader, cohort, income rows, estimator, tabulation rows, tabulator and runner; invented-versus-real guards | DONE | `test_u2_identity.py::test_wrong_target_objects_refuse`; `test_u2_estimator.py::test_context_and_target_guards`; `test_u2_pipeline.py::test_registered_path_refuses_invented_inputs`, `::test_declared_context_refused_for_registered_inputs`, `::test_rows_join_only_the_inputs_the_cohort_was_built_from`; `test_u2_loader.py::test_loaded_inputs_take_the_registered_path_only` |
| Changed source bytes refuse | DONE | `test_u2_mappings.py::test_cited_source_hashes_refuse_changed_bytes`, `::test_a_tampered_shared_document_is_caught_by_the_next_check`, `::test_registries_are_the_pinned_milestone_1_bytes`, `::test_milestone_1b_moved_only_citations_and_prose` (new) |
| Changed frame digests refuse | DONE | `test_u2_loader.py::test_a_changed_frame_breaks_the_seal`; `test_u2_pipeline.py::test_runner_refuses_tampered_invented_inputs` |
| Duplicate identifiers refuse | DONE (completed by this lane) | `test_u2_plans.py::test_duplicate_identifiers_refuse`, `::test_every_keyed_frame_refuses_a_repeated_identifier`; `test_u2_estimator.py::test_duplicate_observation_ids_refuse`; `test_u2_loader.py::test_a_repeated_record_refuses_the_load`; `test_u2_mappings.py::test_parse_refuses_blank_truncated_and_duplicate_records` |
| Failed joins refuse | DONE | `test_u2_plans.py::test_malformed_inputs_refuse` (`missing_family_record_2019`); `test_u2_pipeline.py::test_rows_join_only_the_inputs_the_cohort_was_built_from` |
| Unregistered omissions refuse | DONE | `test_u2_pipeline.py::test_runner_refuses_a_partial_row_set`; `test_u2_identity.py::test_block_rows_with_an_omitted_row_refuse`; `test_u2_plans.py::test_every_target_cell_is_observed_or_disposed_exactly_once` (new) |

## Built in this lane

The lane started from `98c26d8`, where every `tests/track_u2` file passed. It made three commits of code and tests, plus one tier recount:

1. **`9491fb0`, milestone 1b's registry pins.** Milestone 1b changed `roles.json` and `weights.json`, so it moved their pins in `sources.REGISTRY_SHA256` to `5dbd2c13…` and `356fcbd8…`. Both were recomputed from the committed bytes; the old pins equal `883ea48`'s bytes.
   - A leaf-by-leaf diff shows that only citations and prose moved. In roles, entries 7 and 10 changed `open_question`, `part_b_finding`, `corroboration` and one citation line. In weights, entry 2 changed `construction`, `part_b_finding` and `question`, and gained 27 citations.
   - No status, disposition, dependency, action, role or layout field moved. The 2017 cross-sectional weight is still TO VERIFY and still refuses. Its refusal message quotes the revised `question` (`u2_source_registry.py:427`).
   - `test_u2_mappings.py::test_milestone_1b_moved_only_citations_and_prose` pins each registry's gate projection at `883ea48`: every field except citations and five prose keys. The earlier comment cited this test before it existed.
2. **`12e1db0`, duplicate identifiers.** The audit found four duplicate refusals with no test.
   - Executing them on invented inputs found a defect: a repeated 2019 anchor row made `build_u2_cohort` fail on an incidental `TypeError` (`int()` of a Series at the anchor lookup), not a named refusal. A repeated `persons` row would have classified the person's sex as unknown.
   - `cohort.check_unique_identifiers` (`cohort.py:630`) now refuses a repeated `person_id` in persons, design and each wave's anchors, and a repeated `interview` in each wave's income, wealth and DC frames. Its message gives counts, never identifier values.
   - Two named invented variants, `duplicate_family_record_2019` and `duplicate_person_record_2019`, are appended after the others, so every earlier variant is unchanged.
   - The new accounting-identity test covers "unregistered omissions".
3. **`4fcf46e`, tier recount.** See below.

## Invariants stated and tested

Each holds for every input the strategies draw; the Hypothesis tests are in `test_u2_properties.py`.

1. Monotonicity under the cut, per observation, every row and every half of every split: \(R_i\le B_i\) and \(1(R_i<T_i)\ge1(B_i<T_i)\).
2. SSI response bounds: \(0\le\) offset \(\le\) fall \(\le cS\), fall = 0 when \(S\le G\), and offset ≤ FBR room. New enrollment: \(0\le SSI_{new}\le\min(F-C',C-C')\).
3. Zero-cut identity: \(c=0\) gives \(R=B\).
4. Bounds and scale invariance: rates lie in [0, 100], up to the recorded one-ulp rounding of U1's inherited expression. Every rate is invariant to a common positive weight scale.
5. Differential agreement:
   - the U2 estimator equals U1's `adjusted_incomes` on every row both accept (`test_u2_estimator.py::test_u2_estimator_equals_u1_on_rows_both_accept`);
   - the cut and SSI response equal a literal §§7–8 reference (`::test_cut_and_ssi_response_equal_the_section_8_reference`);
   - U1's outputs are byte-identical at `9cee2423` and `12e1db0` (executed).
6. Structure:
   - each one-field row changes only its field (`::test_one_field_rows_change_only_their_field`);
   - the annuity price falls as the interest rate rises (`::test_annuity_price_falls_with_the_interest_rate`).
7. Accounting identity (new): every (target person, plan cell) pair has exactly one disposition, and the observation dispositions are exactly the observations.
8. Determinism and provenance: every invented variant regenerates from (seed, variant) (`test_u2_pipeline.py::test_every_invented_variant_passes_the_regeneration_check`).
9. Registry gate projection: registry changes after the adjudication moved no gate field (new).

One counterexample was found by Hypothesis, then executed and minimized: a single poor observation whose baseline rate is 100.00000000000001. It is recorded as intended rounding (`::test_rate_bound_counterexample_is_a_one_ulp_rounding`), not a bug. The duplicate-anchor `TypeError` was reproduced on a minimal invented variant before it was called a defect.

## Test results

All runs were one file per command with `OMP_NUM_THREADS=1 POLARS_MAX_THREADS=1 .venv/bin/python -m pytest -q -p no:cacheprovider -p no:xdist`, at the code-final commit `12e1db0`.

**`tests/track_u2`, plain (the brief's command): 931 passed, 10 skipped.**

| File | Result |
|---|---|
| `test_adjudication_applied.py` | 20 passed |
| `test_pension_registry.py` | 12 passed |
| `test_psid_research_sources.py` | 391 passed |
| `test_source_registries.py` | 80 passed |
| `test_ssi_capture.py` | 31 passed |
| `test_u2_design_floor.py` | 14 passed |
| `test_u2_differential.py` | 8 passed |
| `test_u2_employer_dc.py` | 32 passed |
| `test_u2_estimator.py` | 25 passed |
| `test_u2_identity.py` | 22 passed |
| `test_u2_isolation.py` | 4 passed |
| `test_u2_loader.py` | 13 passed |
| `test_u2_mappings.py` | 55 passed |
| `test_u2_memo.py` | 14 passed |
| `test_u2_parameters.py` | 18 passed |
| `test_u2_pipeline.py` | 26 passed, 10 skipped (the registered artifact does not exist) |
| `test_u2_plans.py` | 38 passed |
| `test_u2_properties.py` | 17 passed |
| `test_u2_roles.py` | 71 passed |
| `test_u2_scripts.py` | 26 passed |
| `test_u2_worked_cases.py` | 14 passed |

**`-m unit`, `tests/track_u2`: 424 passed, 517 deselected, 0 failed.** These runs used HOME and `POPULACE_DYNAMICS_PSID_DIR` pointed at an empty directory, and an audit hook refusing any open or listing under the PSID directory; no access was refused.

- Passed: pension_registry 12, source_registries 80, ssi_capture 31, design_floor 14, differential 8, employer_dc 32, estimator 25, loader 13, mappings 55, memo 14, plans 38, properties 17, roles 71, worked_cases 14.
- Fully deselected (other tiers): adjudication_applied, psid_research_sources, identity, isolation, parameters, pipeline, scripts.

**The §13 U1 suite, unmodified (the same guard): 390 passed, 39 skipped, 0 failed.** `tests/track_u`:

| File | Result |
|---|---|
| `test_census_threshold_capture` | 56 passed |
| `test_committed_parameters` | 5 passed |
| `test_component_diagnostics_integration` | 1 skipped |
| `test_diagnostics` | 7 passed |
| `test_diagnostics_published` | 4 passed |
| `test_dry_run_script` | 5 passed |
| `test_invented_generator` | 13 passed |
| `test_invented_pipeline` | 2 passed |
| `test_registered_script` | 30 passed |
| `test_rows` | 44 passed |
| `test_runner` | 14 passed |
| `test_ssi_capture_oracle` | 1 skipped |
| `test_threshold_capture_parser` | 6 passed |

The rest of the suite:

| File | Result |
|---|---|
| `tests/cohorts/test_age67` | 27 passed |
| `tests/cohorts/test_age67_integration` | 2 skipped |
| `tests/estimates/test_adjusted_poverty` | 42 passed |
| `tests/estimates/test_adjusted_poverty_u7` | 6 passed |
| `tests/estimates/test_uniform_cut_tabulation` | 25 passed |
| `tests/data/test_family_income` | 38 passed |
| `tests/data/test_family_income_integration` | 11 skipped |
| `tests/data/test_employer_dc` | 19 passed |
| `tests/data/test_employer_dc_integration` | 21 skipped |
| `tests/test_boomers2004_uniform_cut_spec` | 22 passed, 3 skipped |
| `tests/test_replication_boomers2004_uniform_cut` | 25 passed |

Every skip is intentional raw-data or outside-checkout absence, reported as skipped:

- the staged PSID files are absent (35);
- the policyengine-us checkout is absent (1);
- the restriction ledger, the cleared extract and the referee reports are outside this checkout (3).

**Other runs:**

- `tests/estimates/test_birth_evidence_artifact.py`: 13 passed.
- `tests/test_benchmarks.py`: 10 passed.
- `tests/test_tier_policy.py`, against a full collection: 1 passed, 9,408 deselected.

**Black and Ruff:** clean on `src/populace_dynamics/uniform_cut_track_u2/`, `tests/track_u2/`, the U2 scripts and `scripts/u2_u1_differential.py`. Black (`-l 79 --check`) leaves all 42 files unchanged, including `scripts/first_estimates_birth_evidence.py` and its test. Ruff reports "All checks passed".

**Tier recount** (`recount-tiers.py .`, collection only, `-p no:xdist`, the refusing hook active and never triggered): unit 4,108, artifact 3,258, integration_psid 1,341, reproduction_legacy 520, oracle_policyengine 182; total 9,409. That equals the full collection, with no errors.

## U1 differential evidence

The §13 differential was executed, not only specified. The command:

```text
python scripts/u2_u1_differential.py --base <detached 9cee2423> --candidate <detached 12e1db0> --output <json>
```

It ran with the repository `.venv` interpreter for both sides, fresh detached worktrees (both `git status` clean), and the refusing PSID hook active. The result:

- **Pass:** `all_equal: true`, `all_checks_passed: true`, `dry_run_skipped: false`, exit 0.
- **Dry run** (seed 20260924, entire canonical JSON minus `/run/git_head` and `/run/date`, and normalized Markdown):
  - JSON equal, SHA-256 `8d7dd8ef2d88ae18058edccdf7524fff533847f0381d78c5aa3ed391032ad07a` on both sides;
  - Markdown equal, `407b490245005224757d8dbf33442db42a7e49d5f9315617d4f9a9122b009ff2` on both sides;
  - `git_clean` true on both; `run.command` equal.
- **Contract probe:** equal, `49e47726948dc6faf4f39e0ae1ff60054e178b5feb4701cbb8b84400b6bdccd9` on both sides. It checked `actual_loader`, `age67.WAVES`, `input_frames_sha256`, `observation_plan`, `pending_decisions`, `refusal_parity`, `rows.MAX_RULINGS`, `runner.NAMED_DELTAS`, `COMPARATOR_COLUMN` and `REPORT_ROWS`.
- **Refusal parity:** all ten cases met their fixed expectations at both commits.
- **Actual-loader probe:** no file access under the fake PSID root.
- **Ratified U1 block:** SHA-256 `aed6e724…`.

The harness's report is committed as [`u2_m2_u1_differential_12e1db0.json`](u2_m2_u1_differential_12e1db0.json) (SHA-256 `cec6bc8eab061f39811964f671f6a72d56a14dd3d6558466955a745eda17d006`). The commits after `12e1db0` change no Python file.

## Invented dry run (head)

`scripts/track_u2_dry_run.py --output-dir <scratch>` at `12e1db0` exited 0 with no PSID access. `RESULTS.md` begins:

```text
# INVENTED DATA - NOT A COMPARISON

U2 (Boomers 2004, column 1946-55) invented end-to-end dry run, 2026-09-29. Every person, family, amount, weight and sampling stratum and cluster is **invented** (`populace_dynamics.uniform_cut_track_u2.invented`, seed 20260928); so are the poverty thresholds. No PSID file was opened, no comparator value was read, and nothing below is a result, a forecast or a comparison with DYNASIM.

Labels: *INVENTED DATA - NOT A COMPARISON*; *PSID-realized outcomes (not a projection)*; *Python income concept (not Axiom)*; *mechanical incidence*.
```

Its checks section records:

- the rows and named deltas equal §15 and §12;
- the draft rulings are refused;
- the plans equal the support registry;
- round trips in all six waves;
- the registry gate refuses 2015–2023;
- every named variant's branch or refusal (the two duplicate variants are refused builds);
- the registered runner and parameter check refuse invented inputs;
- nine cross-cohort refusals;
- per-observation monotonicity and SSI bounds in all ten rows and every half.

Code `12e1db0` (worktree clean: True), invented frames SHA-256 `fade81d6…`. Its tabulated numbers describe invented data only and are not reproduced here.

## Conservative readings

Where the specification is silent, the code takes the most conservative reading and says so:

1. **Unregistered cohort settings refuse** (§§3, 15; `cohort.py:199–203`). U2 registers one value for each `U2CohortSpec` field, so any other value refuses.
2. **Two occupants of the spouse income slot refuse the income rows** (§3; `test_u2_roles.py:355–356`). The specification leaves an ambiguous *pairing* unresolved and counted, but is silent on two slot occupants.
3. **Code 88 and the historical combined spouse-retirement crosswalk refuse in every context** (§3; `sources.py:38–40`). The specification declares no substantive rule for either.
4. **Only the §15 block is the contract** (`rows.py:351`). §16a's proposed amendments, including its `previous_routes` fragment, are never read as the block.
5. **Pre-registration evidence is gated through ratification** (§14). The preflight refuses while `blocked_by` names the mapping review or the pre-registration pass. The loader's source preflight refuses while any applied entry is TO VERIFY or blocked. No evidence-file format is specified, so none is invented.
6. **An exact memo endpoint is on the edge, not inside** (§10a; `memo.py:18–20`). The same endpoint rule applies to the level allowance.
7. **The declared gate runs on invented records only** (§§3, 15; `sources.py` docstring). It applies the §3 role table and §15 routes so the dry run can exercise each branch. The registered path builds its own registry gate, and the runner refuses to record the declared gate for a registered run.
8. **Duplicate-identifier messages give counts, never identifier values** (§14; `cohort.py:630`). This lane's reading, since identifiers on real data are PSID person and interview numbers.

## Not done

- **Real-data steps (§20 step 4 onward).** These need separate authorization: the structural, reconciliation and F17 pass, and the registered one-shot that would write the artifact and sidecar.
- **Ratification of `u2-draft-4` and the §16a amendments by Max.** Until then the registries' open and refused routes refuse, and so does the registered preflight.
- **The optional structure-only U1 load (§13).** It needs Max's explicit OK.
- **Independent review of `9491fb0` and `12e1db0`.** These two commits postdate the three review rounds; they are small and fully tested.
