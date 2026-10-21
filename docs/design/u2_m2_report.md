# U2 milestone 2 report: implementation on invented data

**INVENTED DATA - NOT A COMPARISON.** Milestone 2 builds everything in specification §14's implementation table, and every §13 test, without running anything on real data. The specification is [`boomers2004_1946_55_comparison.md`](boomers2004_1946_55_comparison.md) (`u2-draft-4`, unratified). This report has five parts:

- the §13/§14 completeness audit;
- what the finishing lane built;
- the invariants and their tests;
- the test and differential evidence;
- the conservative readings and what remains.

The exposure record is [`u2_m2_exposure.md`](u2_m2_exposure.md).

- **Branch:** `dynamics-u2-m2-20260928`, rebased onto `b948d6b` (milestone 1b's fixed head, which includes milestone 1 and the applied source adjudication at `883ea48`).
- **Code-final commit:** `ed82c02d`, the round-3 closeout's. Milestone 2 itself was code-final at `12e1db0`; review rounds 1 to 3 and the closeout changed the code after it. Later commits change only `docs/design/` and, at master merges, the tier files.
- **Round 1 review fixes:** `0d742fd`, `8ec6953`, `9368931` and `b211ee7` answer the independent review of `f946334` ("Round 1 review fixes", the last section).
- **Round 3 informational fixes:** `5e8524c`, `77a17ce`, `380f52b`, `75c16d5`, `c27e46f` and `c2f15bc` answer the three informational items the approving round-3 review of `34e3f65` left, and what three rounds of adversarial verification found ("Round 3 informational fixes").
- **Round 3 closeout:** `183c7ef3` merges master `9af53921`. `e08b98dd`, `fcfc4025` and `ed82c02d` answer the closeout review of `183c7ef3`, the fourth-pass mutation run and the delta review of `a1858bb9` ("Round 3 closeout", the last section).
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

## Round 1 review fixes (2026-09-29)

The independent review of `f946334` returned **U2-M2: REQUEST CHANGES**: one blocking finding, one to fix before ratification, one low and two informational. A blind builder lane (workflow subagent, Claude Opus 5.5) fixed all five. For findings 1–3 and info 5 it wrote tests, ran them against `f946334`'s code, where they failed, and against the fix, where they passed. Info 4 strengthens an existing property, which passes on both. The exposure record for this lane is in [`u2_m2_exposure.md`](u2_m2_exposure.md#round-1-fix-lane). **INVENTED DATA - NOT A COMPARISON:** every case below uses invented persons, invented staged files or invented altered values.

| Finding | Fix | Commit | Tests |
|---|---|---|---|
| 1 (medium, blocking): individual-file values never checked against the registry's documented codes | `loader.check_individual_values` (`loader.py:852`) refuses any value outside the entry's `codes`, or outside the restated codebook range for fields without codes (`loader.py:141`), with the named `U2UndocumentedValue`. Sex maps 1/2/9 explicitly. `RoleContext.rule` (`sources.py:829`) refuses a code the wave does not document, and code 0 on an in-family member, instead of returning the OFUM rule | `0d742fd` | `test_u2_loader.py`: 12 undocumented cases (the review's sex 2→5 and relationship 90→99 among them), 4 documented controls, message, codebook-text, role-rule and one Hypothesis property |
| 2 (medium, fix before ratification): PSID file hashes and frame digest neither bound nor rechecked | a pre-registration evidence record (`loader.preregistration_evidence`, `loader.py:657`), written by `track_u2_structure.py`; `load_u2_inputs(evidence=…)` rehashes every frozen file before any parse and refuses a changed file set or frame digest (`loader.py:709`, `:734`); the registered preflight refuses while the record is absent and binds its hash, file hashes and frame digest (`run_track_u2_registered.py:177`, `:297`); a registered run needs the sealed recheck (`runner.py:146`) | `8ec6953` | `test_u2_loader.py` (one-byte, missing-file, frame-digest, unfrozen-file, malformed-record, forged-seal cases and a Hypothesis property); `test_u2_scripts.py` (binding, absent record, other identities, `main` wiring and a Hypothesis property) |
| 3 (low): the registered parameter check trusted the provenance label | `parameters_content_sha256` (`parameters.py:389`) digests the numbers only; the registered branch compares them with a fresh hash-verified read of the pinned files (`parameters.py:542`) | `9368931` | `test_u2_parameters.py`: 9 single altered values under pinned labels, in-place edit, extra year, digest semantics and one Hypothesis property |
| Info 4: monotonicity property low power | 200 examples (was 25) and an 8-ulp bound on max(\|B\|, \|R\|, S) instead of an absolute 1e-6 | `b211ee7` | `test_u2_properties.py` |
| Info 5: an anchor person missing from `persons` read as sex unknown | `cohort.check_person_joins` (`cohort.py:687`) refuses, in the build and the birth derivation | `b211ee7` | `test_u2_plans.py::test_an_anchor_person_without_a_persons_record_refuses` |

The dry run now also records the round-1 refusals (`track_u2_dry_run.py:156`), and `test_u2_scripts.py` asserts the error class of each.

### Before and after

The review's exact cases were run as a script against `f946334`'s code and then against the fixed code. The script used the invented population, invented staged files and the real loader with the tests' four patches.

| Case (invented) | `f946334` | Fixed |
|---|---|---|
| Sex 2→5 for 700031 | loaded; sex read as `na` | `U2UndocumentedValue` (`common.sex`, undocumented code 5) |
| Relationship 90→99 for 700142, 2015 | loaded; code 99 kept | `U2UndocumentedValue` (`2015.relationship`, undocumented code 99) |
| One digit changed in `family/2019/FAM2019ER.txt` after freezing | loaded, with a changed frame digest | `U2FrozenIdentityMismatch` (1 frozen file changed), before any record is parsed |
| Weighted average set to 1.0 under the pinned Track M label | accepted by the registered check | `U2ParameterError` (content differs from the pinned captures) |

New tests against `f946334`'s code:

- **Finding 1:** 16 failed and 4 passed. The 4 documented-value controls pass on both sides. Ten undocumented cases loaded silently. A negative weight was refused only by the old generic check. A blank field crashed with `IntCastingNaNError`.
- **Finding 2:** every new test fails, because the APIs do not exist.
- **Finding 3:** 13 of 14 fail; the pinned-bundle control passes.
- **Info 5:** the new test fails, and `derive_u2_births` accepted the unjoined person.

After the fix, every new test passes.

### Invariants stated and tested (round 1)

10. **Documented domain.** For every individual-file field U2 reads and every integer value, the value check refuses a record holding it iff the registry does not document it. This is `test_u2_loader.py::test_the_individual_check_accepts_exactly_the_documented_domain`, 200 examples. The restated ranges are held to every wave's codebook text.
11. **Frozen bytes.** Changing any single byte of any frozen file to any other byte makes the pre-read recheck refuse; with the bytes restored, it passes. This is `::test_every_single_byte_change_to_any_frozen_file_refuses`, 100 examples.
12. **Binding injectivity.** Changing any one frozen file hash, or the frame digest, changes the registration binding's SHA-256. This is `test_u2_scripts.py::test_the_binding_changes_with_every_frozen_identity`, 100 examples.
13. **Parameter content** (restated in round 2; the round-1 wording, "accepts ... iff every value equals the pinned files'", was false, see [round 2](#round-2-review-fixes-2026-09-29); round 3 states the precondition, see [round 3](#round-3-informational-fixes-2026-09-29-to-2026-10-11)). The precondition is that the bundle's labels name U2's pinned sources: its `target_id` is `U2`; `thresholds.provenance` records kind `census_capture`, the pinned Track M Census SHA-256 and target `U2`; `ssi.provenance` records kind `policyengine_us_capture`, the pinned U2 SSI SHA-256 and target `U2`; and the life tables `nchs_2000` and `ssa_period_2004` each carry their pinned SHA-256 in `source`. The registered check accepts a bundle that meets the precondition iff two things hold. First, its digested content (every threshold and SSI value, and each life table's name and `qx`, with their keys) is built only from the pinned loaders' types: `U2Parameters`, `PovertyThresholds`, `SsiParameters` and `LifeTable` exactly, with no instance attribute beyond their fields; plain `dict` and `tuple` containers; `int` years and child counts; `str` rows, sexes, bases and names; and `float` values, or `int` values exactly equal to a float. Second, it has the pinned files' keys, each life table carries its pinned name (its basis), and every value equals, as a number, the value read afresh from them. The labels are read only as the precondition states; their containers' types are not checked. Moving one value anywhere in the thresholds, SSI or life tables refuses (`test_u2_parameters.py::test_any_single_altered_value_refuses_the_registered_check`, 150 examples). So does adding any colliding key at any depth of any threshold or SSI schedule (`::test_no_colliding_key_passes_the_registered_check`, 200 examples). A rebuild of the pinned values in fresh containers, in any order, passes (`::test_a_canonical_rebuild_of_the_pinned_values_passes`, 60 examples). A bundle that fails the precondition is refused on its labels alone, whatever its values: the content digest reads no label, so a bundle holding exactly the pinned values under any one changed label keeps the pinned digest and is still refused (`::test_every_precondition_label_is_necessary`, 90 examples).
14. **Monotonicity bound.** Invariant 1 is now checked as \(R_i\le B_i+8\,\mathrm{ulp}(\max(|B_i|,|R_i|,S_i))\).
    - The estimator computes \(R=((B-\mathrm{cut})+\mathrm{offset})+\mathrm{new}\) (`estimator.py`, `u2_adjusted_incomes`), so R can exceed B only by rounding.
    - Over 71,670 invented observation-rows (1,500 drawn frames, every registered row), the largest excess was 1 ulp. Exact comparison would therefore be wrong.

### Conservative readings (round 1)

9. **Domains for fields the registry lists no codes for** (§14; `loader.py:141`). These are restated from each entry's `codebook_text`, and a test holds them to that text:
   - age: 0, 1–125 or 999;
   - year born: the entry's `missing_codes` (0, 9999), or 1870 through the wave year;
   - interview: 0–99,999, the five-column field;
   - the 1968 family and person numbers: at least 1;
   - weight: finite and nonnegative, because the registry says not to infer a domain from the printed range.

   A field with neither codes nor a restated domain refuses.
10. **Relationship code 0 on an in-family member refuses** (§14; `sources.py:829`). The codebooks document 0 as "Inap.", not a relationship to the head.
11. **The evidence record's format and place** (§14, §20 steps 4 and 8). This supersedes reading 5's "no evidence-file format is specified, so none is invented": the review answered that a hashed evidence record is needed.
    - The schema is `populace_dynamics.track_u2_preregistration_evidence.v1`, holding exactly the target, specification, registry pins, cited-source hashes, PSID file hashes, their bundle and the frame digest.
    - It records no data-directory path; files are keyed relative to that directory.
    - Once reviewed, it is committed at `docs/design/u2_preregistration_evidence.json`. `runs/` and `data/external/` are held unchanged by `test_u2_isolation.py`.
    - It does not exist yet, so the registered preflight refuses. The existing `blocked_by` refusal is unchanged.
12. **A registered run requires the sealed recheck** (§14, "execution rechecks their frozen identities"; `runner.py:146`). This goes beyond the finding, which asked only for the preflight and the loader: `run_track_u2` itself refuses registered inputs the loader did not recheck. The source-gate check now runs before the input guard, so the declared-gate refusal keeps its name.
13. **Invented runs keep label-only parameter checks.** The content check applies to registered runs, whose only admissible values are the pinned captures.

### Test results (round 1, final code `b211ee7`)

**Every `tests/track_u2` file, one per command, with `-p no:xdist`: 995 passed, 10 skipped, 0 failed.** The 10 skips are the registered artifact's absence.

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
| `test_u2_loader.py` | 58 passed (was 13) |
| `test_u2_mappings.py` | 55 passed |
| `test_u2_memo.py` | 14 passed |
| `test_u2_parameters.py` | 32 passed (was 18) |
| `test_u2_pipeline.py` | 26 passed, 10 skipped |
| `test_u2_plans.py` | 39 passed (was 38) |
| `test_u2_properties.py` | 17 passed |
| `test_u2_roles.py` | 71 passed |
| `test_u2_scripts.py` | 30 passed (was 26) |
| `test_u2_worked_cases.py` | 14 passed |

Other runs:

- **`tests/estimates/test_birth_evidence_artifact.py`:** 13 passed.
- **The §13 U1 suite, unmodified:** 390 passed, 39 skipped, 0 failed, the same files and counts as above.
  - It ran with HOME and `POPULACE_DYNAMICS_PSID_DIR` pointed at an empty directory.
  - An audit hook refused any open or listing under `~/PolicyEngine/psid-data`; it refused nothing.
- **Black (`-l 79`) and ruff** are clean on every changed file.
- **Tiers** (`recount-tiers.py`, collection only):
  - unit 4,154 (+46);
  - artifact 3,276 (+18);
  - integration_psid 1,341;
  - reproduction_legacy 520;
  - oracle_policyengine 182;
  - total 9,473.
- **Isolation:** no protected file changed (`data/family.py`, `data/psid.py`, `estimates/career.py`, `engine/*`, `gates.yaml`, `runs/*.json`), and no new source module was added, so `POST_REVIEW_SOURCE_EXCLUSIONS` is unchanged. `test_u2_isolation.py` and the birth-evidence test pass.

### Not done (round 1)

- **The evidence record itself.** It is written by the §20 step-4 structure pass on real data, which is separately authorized. This lane ran nothing on real data.
- **Independent review of `0d742fd`–`b211ee7`.**

## Round 2 review fixes (2026-09-29)

The independent review of `eeb4850` returned **U2-M2: REQUEST CHANGES**. Round 1's findings 1 and 2 and info items 4 and 5 were resolved. Finding 3 was partial, one low finding, which was the only change requested. There were also two informational items. A blind builder lane (workflow subagent, Claude Opus 5.5) fixed the low finding and both informational items, and closed one related gap the review did not name. For each fix it wrote tests first and ran them against `eeb4850`'s code, where they failed, then against the fix, where they pass. The exposure record for this lane is in [`u2_m2_exposure.md`](u2_m2_exposure.md#round-2-fix-lane). **INVENTED DATA - NOT A COMPARISON:** every altered value below is invented (1.0, or a monthly FBR of 1.0 read as 12.0 a year), every input is the invented population or its invented staged files, and no real PSID record was read.

| Finding | Fix | Commit | Tests |
|---|---|---|---|
| 1 (low): the content digest was not injective. `str(int(key))` let a key such as `2012.5` stand beside `2012`, hold the pinned value and hide an altered one that the estimator reads by exact key (`adjusted_poverty.py:1028-1054`, `:1069-1075`) | `parameters_content_sha256` (`parameters.py:481`) reads only the pinned loaders' exact types. The classes must match exactly with no extra instance attribute (`_exact_instance`, `parameters.py:407`); containers must be plain `dict` or `tuple` (`_plain`, `:427`); keys must be exact `int` or `str` (`_key`, `:438`); values must be floats or ints exactly equal to a float (`_number`, `:449`). On that domain the key encoding is injective, and any other type raises `U2ParameterError` | `f78df52` | `test_u2_parameters.py`: the review's three collisions plus a string year key and an object row key; dict-subclass, tuple-subclass, `SsiParameters`-subclass and shadowed-method bundles, each shown to change what the run reads; four value types; a bundle subclass; a Hypothesis property over every key depth (200 examples); and a converse property (60 examples) |
| Beyond the findings: check, then use | `check_u2_parameters` now returns the bundle a run computes with. For a registered run that is the fresh read of the pinned files the caller's bundle was just shown equal to (`parameters.py:691`), and `run_track_u2` uses it (`runner.py:485`). Anything the caller still holds, such as an in-place edit made from the progress callback, cannot reach a row | `b1d95c8` | `test_u2_loader.py::test_a_registered_run_computes_with_the_fresh_pinned_read` |
| Info 2: `check_inputs` accepted any 64-hex sealed evidence hash and never compared it with the bound one | `check_inputs` and `run_track_u2` take `preregistration_evidence_sha256`. A registered run refuses unless it is given and equals the loader's sealed hash (`runner.py:172-185`); an invented run refuses one (`runner.py:124`). `main` passes the hash its preflight bound (`run_track_u2_registered.py:367`) | `b1d95c8`; `f16f1b9` names the given value in the malformed-hash refusal | `test_u2_loader.py`: unnamed, other-record and malformed hashes, an invented run naming one, and a mismatch refusing before any computation; `test_u2_scripts.py::test_the_registered_main_passes_the_bound_evidence_hash_to_the_run` |
| Info 3: the open question on the spouse-sex lookup | No code change; the reviewer's answer was checked against the code (below) | none | `test_u2_plans.py::test_an_anchor_person_without_a_persons_record_refuses` (round 1) |

The dry run records the round-2 refusals (`track_u2_dry_run.py:228`), and `test_u2_scripts.py` asserts the error class of each: the three collisions, an `SsiParameters` subclass and an invented run naming an evidence hash.

**Info 3, checked against the code.** The spouse-sex lookup `sex.get(int(spouse), "na")` (`cohort.py:1053`) runs only when `coresident` is true. That requires `int(spouse) in members` (`cohort.py:1044-1047`), where `members` are the family's rows. Those rows are the in-family rows of `inputs.anchors[wave]` (`cohort.py:941-950`, `:989`), and `build_u2_cohort` first calls `check_person_joins` (`cohort.py:922`). That function refuses any anchor person without a `persons` record (`cohort.py:687-706`), so the lookup cannot silently read `na` for a missing join. The review said the same of the head, slot and legal-spouse lookups (`cohort.py:1104-1133`). This lane did not reread those lines.

### Before and after

Each case was run as a script, or as a temporary uncommitted test, against `eeb4850`'s code and then against the fixed code. Every provenance label named the pinned captures.

| Case (invented altered value) | `eeb4850` | Fixed |
|---|---|---|
| Weighted-average key `2012.5` holding the pinned 2012 rows, `2012` `one_65_plus` set to 1.0 (review case 1b) | accepted; the run reads 1.0 | `U2ParameterError` (float key) |
| Couple FBR key `2018.5` holding the pinned value, 2018 set to 1.0 a month (review case 2) | accepted; the run reads 12.0 a year | `U2ParameterError` (float key) |
| Matrix child key `0.5` holding the pinned cell, 2016 `three` column 0 set to 1.0 (review case 3) | accepted; the run reads 1.0 | `U2ParameterError` (float key) |
| Year key `"2012"` (a string) holding the pinned rows | accepted; the run reads 1.0 | `U2ParameterError` (str key) |
| A row key object whose `str()` is `one_65_plus` | accepted; the run reads 1.0 | `U2ParameterError` (non-str key) |
| A `dict` subclass whose `__getitem__` returns 1.0 for 2012 | accepted; the run reads 1.0 | `U2ParameterError` (not a plain dict) |
| A `tuple` subclass slicing NCHS female `qx` to 1.0 | accepted; the survival curve reads the 1.0s | `U2ParameterError` (not a plain tuple) |
| An `SsiParameters` subclass overriding `fbr_annual` | accepted; the run reads 12.0 | `U2ParameterError` (not exactly `SsiParameters`) |
| An instance attribute shadowing `fbr_annual` | accepted; the run reads 12.0 | `U2ParameterError` (instance attribute) |
| A `float` subclass in `qx` whose `float()` is the pinned value | accepted; the run reads the pinned value, so not a bypass | `U2ParameterError` (non-canonical type) |
| The caller edits its bundle after the check (from the progress callback) | the row read the edited 1.0 | the row reads the fresh pinned bundle |
| Registered `check_inputs` with loader-rechecked inputs and no bound hash named | accepted | `U2RunError` (must name the bound hash); another hash also refuses |

New tests against `eeb4850`'s code:

- **Finding 1:** 15 of 16 new tests fail.
  - Twelve fail with `DID NOT RAISE`: the five collision cases, the four pinned-field routes, the `str` and float-subclass values, and the bundle subclass.
  - The collision property fails on its first example.
  - The int beyond 2^53 and the bool fail on the message only: the old content comparison refused them because they differ from the pinned number, not because of their type.
  - The converse property passes on both sides, as intended.
- **Info 2 and the check-then-use gap:** all 8 new tests fail, 7 with `TypeError` (the keyword did not exist) and the `main` wiring test because `main` passed no hash. The existing registered-path test was updated to the new keyword. The table's last two rows are the temporary probe's behavioural evidence.

After the fix, every new test passes.

### Invariants stated and tested (round 2)

13. **Parameter content**, restated above. It adds the collision property and its converse.
15. **Fresh parameters.** A registered run computes with the fresh read of the pinned files, never the caller's objects, so an edit to the caller's bundle after the check reaches no row (`test_u2_loader.py::test_a_registered_run_computes_with_the_fresh_pinned_read`).
16. **Bound evidence.** A registered run proceeds only if the evidence hash the loader sealed equals the hash the registration binds, and `main` passes the bound one (`test_u2_loader.py::test_a_registered_run_needs_the_evidence_its_registration_binds`, `test_u2_scripts.py::test_the_registered_main_passes_the_bound_evidence_hash_to_the_run`).

### Conservative readings (round 2)

14. **Exact types in a registered bundle** (§14; `parameters.py:407-478`). A float subclass (numpy's `float64` among them), a `str` or `bool` value, or an int no float equals refuses, even where it converts to the pinned number. The pinned loaders build none of these, so no genuine registered bundle is refused (the converse property).
15. **Integer-valued floats stored as ints still pass, and the sign of zero is ignored** (`parameters.py:449`). These are equal numbers, and round 1's digest test already allowed the first.
16. **A registered run substitutes the fresh pinned read only after proving equality** (§14; `parameters.py:691`). It never substitutes silently: any other bundle still refuses.

### Test results (round 2, final code `f16f1b9`)

**Every `tests/track_u2` file, one per command, with `-p no:xdist`: 1,018 passed, 10 skipped, 0 failed.** The 10 skips are the registered artifact's absence.

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
| `test_u2_loader.py` | 64 passed (was 58) |
| `test_u2_mappings.py` | 55 passed |
| `test_u2_memo.py` | 14 passed |
| `test_u2_parameters.py` | 48 passed (was 32) |
| `test_u2_pipeline.py` | 26 passed, 10 skipped |
| `test_u2_plans.py` | 39 passed |
| `test_u2_properties.py` | 17 passed |
| `test_u2_roles.py` | 71 passed |
| `test_u2_scripts.py` | 31 passed (was 30) |
| `test_u2_worked_cases.py` | 14 passed |

Other runs:

- **`tests/estimates/test_birth_evidence_artifact.py`:** 13 passed.
- **The §13 U1 suite, unmodified:** 390 passed, 39 skipped, 0 failed; the same files and counts as round 1.
  - It ran with HOME and `POPULACE_DYNAMICS_PSID_DIR` pointed at an empty directory.
  - An audit hook refused any open, listing or stat under `~/PolicyEngine/psid-data`. It refused nothing.
- **U1 differential, rerun at `f16f1b9` against `9cee2423`** (`git clone --shared` clones in a scratch directory, with the refusing hook active):
  - `all_equal` and `all_checks_passed` are true;
  - dry-run `result.json` and `RESULTS.md` are byte-equal;
  - the contract probe is equal (`49e47726…` on both sides, as in round 1);
  - refusal expectations are met at both commits;
  - no loader file was accessed.

  The report is committed as [`u2_m2_u1_differential_f16f1b9.json`](u2_m2_u1_differential_f16f1b9.json) (SHA-256 `bd347db0b1dcbe680e28c1bd9a577cad1ff9dbb82b75b93def7806f80f0a8e02`). An earlier run at `b1d95c8` gave the same verdicts. The commit that records the report changes no Python file.
- **Black (`-l 79`) and ruff** are clean on `src/populace_dynamics/uniform_cut_track_u2/`, `tests/track_u2/` and the two changed U2 scripts.
- **Tiers** (`recount-tiers.py`, collection only, `PYTEST_ADDOPTS=-p no:xdist`, the refusing hook active and never triggered):
  - unit 4,160 (+6);
  - artifact 3,293 (+17);
  - integration_psid 1,341;
  - reproduction_legacy 520;
  - oracle_policyengine 182;
  - total 9,496.

  `test_tier_policy.py` passes against the full collection: 1 passed, 9,495 deselected.
- **Isolation:**
  - No protected file changed: `data/family.py`, `data/psid.py`, `estimates/career.py`, `engine/*`, `gates.yaml` and `runs/*.json`.
  - No new source module was added, so `POST_REVIEW_SOURCE_EXCLUSIONS` is unchanged.
  - No milestone-1b-owned file was touched.

### Not done (round 2)

- **The evidence record itself**, as in round 1. It is written by the §20 step-4 structure pass on real data, which is separately authorized.
- **Independent review of `f78df52`, `b1d95c8` and `f16f1b9`.**

## Round 3 informational fixes (2026-09-29 to 2026-10-11)

The round-3 independent review of `34e3f65` returned **U2-M2: APPROVE**. It left three informational items, none reachable through `scripts/run_track_u2_registered.py`'s `main`:

1. a seal forged in-process passed the evidence-binding check;
2. a registered run checked only the row ids of `row_set`;
3. invariant 13's restatement left out a precondition.

This lane fixed all three. It was the main session (Claude Opus 5.5), working as a blind builder from `cd51fcb`, then rebased onto master after #487 merged.

The lane then attacked its own fix in three adversarial rounds. Each round used blind in-session workflow subagents (Claude Opus 5.5) on invented data, and each found a bypass the fix did not close. A fourth-pass mutation run went to a Subfleet lane (GPT-6.1 Sol). The fixes therefore came in four passes; the third changes how a registered run treats its inputs. The run checks its inputs and then uses only what it checked:

- it computes only on frames parsed from the exact text whose SHA-256 the bound record froze;
- it records provenance from that record.

For every fix, the tests were written first and failed on the code before the fix. The exposure record is in [`u2_m2_exposure.md`](u2_m2_exposure.md#round-3-fix-lane).

**INVENTED DATA - NOT A COMPARISON:** every altered value is invented. That means offsets of +5 (+1 to +1000 in the properties), a swapped sex label, an invented zero and invented computed floats. Every input is the invented population or its invented staged files. No real PSID record was read.

| Item | Fix | Commit | Tests |
|---|---|---|---|
| Info 1: a seal written with `object.__setattr__` over altered frames passed, because the runner held only the evidence hash | `check_inputs` and `run_track_u2` take the evidence record as well as its bound hash. A registered run refuses unless the record is valid and hashes to the bound value (`_bound_evidence`, `runner.py:355`). The inputs' frame digest, PSID file hashes and cited-source hashes must equal the record's (`runner.py:305-343`). `main` passes the record its preflight read (`run_track_u2_registered.py:372`) | `5e8524c` | `test_u2_loader.py`: the review's probe B2, the record-backed refusal, relabelled file and cited hashes, three wrong records, an invented run naming a record, refusal before any computation, and a Hypothesis property over every numeric cell of every input frame (100 examples); `test_u2_scripts.py`: `main` wiring |
| Info 2: a registered run checked only the row ids | A registered run refuses any `row_set` (`runner.py:657`), even `REGISTERED_ROWS` itself, and computes exactly the rows `main`'s preflight binds | `5e8524c` | `test_u2_loader.py`: the review's probe B3, the default computes the registered rows, and a Hypothesis property refusing every row set before any check (60 examples); `test_u2_pipeline.py`: an invented run still accepts the ten rows given explicitly |
| Info 3: invariant 13 omitted its precondition | The report states the precondition (the labels name U2's pinned sources). The verification added life-table names to the content clause. The property tests' docstrings and `parameters_content_sha256`'s docstring match | `77a17ce`, `75c16d5` | `test_u2_parameters.py::test_every_precondition_label_is_necessary` (90 examples), `::test_life_table_names_are_content` |
| Found while fixing: a provenance label with rigged comparisons skipped the row-set guard while the registered checks ran | The label must be exactly one of the two strings (`_check_provenance_label`, `runner.py:123`) | `5e8524c` | `::test_a_registered_run_takes_only_an_exact_provenance_label` |
| Found while fixing: frames edited while the parameter check read the caller's provenance, with the seal forged again, reached the rows | The births must carry the frozen digest (`runner.py:721`). Since the third pass the rows compute on the snapshot, so such an edit reaches no row, and the births check is a backstop that no public-API input reaches (closeout review, finding 5) | `5e8524c`, `c27e46f` | `::test_frames_changed_after_the_check_reach_no_row` |
| Round 1: a `str` subclass in the record, bound hash or seal compared equal to anything | The record must be plain JSON data by exact type (`loader._plain_json`, `loader.py:711`). Both hashes must be exactly `str` (`runner.py:278`, `:290`) | `380f52b` | three malformed-record cases; rigged digest, bound and seal cases; a test that kills the record-hash guard by its own attack |
| Round 1: a `dict` subclass container served the digest one frame and the rows another; a `str`-subclass cell or label kept its text but compared as another value | The digest reads only plain dicts keyed by exact `int` (`_wave_frames`, `cohort.py:594`), exact-`str` labels and exact-`str` string cells (`_check_frame_types`, `cohort.py:499`) | `380f52b`, `c27e46f` | a Hypothesis property over 4 containers × 6 lying methods (40 examples); the verification's minimized `how_ended` case and a property over every string cell (40 examples); label, Index-subclass, dtype, dtype-subclass, wave-key and object-column cases |
| Round 1: `RoleContext.rules` rewritten after construction kept the `registry` kind | `check_inputs` compares the caller's rules with the committed ones as canonical text (`sources.role_rules_text`, `sources.py:839`; `runner.py:261`). The rows get a fresh committed context (`runner.py:712`). `RoleRule` is final | `380f52b`, `c27e46f` | rewritten-rules, fresh-context and final-and-bound-by-text tests |
| Round 2: an object in a frame's `attrs` runs code whenever pandas copies the frame; an ExtensionArray subclass keeps the exact dtype and CSV text while the rows read other values | **Check, then use.** `cohort._registered_snapshot` (`cohort.py:735`) writes each frame's text once as the digest writes it and hashes it. It then parses a private frame from that text, which must write the same text again (`_rebuild_frame`, `cohort.py:671`). A registered run compares that digest with the record and computes only on the snapshot (`runner.py:310`, `:694`). The digest also refuses `attrs` (checked first), empty string cells, and any dtype outside the seven the loader and U1's readers build (`_FRAME_DTYPES`, `cohort.py:465`). The step-4 evidence writer refuses frames that do not rebuild (`loader.py:851`), so such a refusal comes before registration | `c27e46f` | attrs, rigged-array and snapshot-provenance tests; the loader's and generator's frames rebuild value for value; the step-4 refusal |
| Round 2: the recorded provenance came from the caller's mutable inputs | The snapshot's provenance consists of the bound record's PSID file, bundle and cited-source hashes plus the committed registry pins. It has no data directory and is marked `registered_snapshot` (`SNAPSHOT_KEY`, `cohort.py:178`). The inputs' recorded hash maps must be plain dicts of exact `str` (`_plain_hashes`, `runner.py:184`) | `c27e46f`, `c2f15bc` | snapshot-provenance and rigged-recorded-hash tests |
| Round 2: a caller-edited source-gate audit and a `str`-subclass pointer were recorded | A registered run takes no source gate, since it applies none. The pointer must be exactly a `str` (`runner.py:688`, `:238`) | `c27e46f` | source-gate and pointer tests |
| Round 3: `RoleContext` stored the cached committed `RoleRule` objects, so every context shared them, the run's fresh one included, and a progress callback could edit them in place. The third pass introduced this regression | Each context holds private copies (`sources.py:1128`). A role-registry refusal in the runner is a `U2RunError` (`_committed_roles`, `runner.py:346`) | `c2f15bc` | private-rule-object and callback-edit tests; the role-refusal wrapping |
| Round 3: pandas' default float parser misreads some 16–17-digit reprs, so a frame holding computed floats would have been falsely refused at step 4 | The rebuild parses floats with the round-trip converter (`cohort.py:696`) | `c2f15bc` | the verification's computed weight `0.013 × 8,950,792`; a strict Hypothesis property: every frame over the allowed dtypes, with full-precision floats, rebuilds exactly, and no refusal passes (300 examples) |
| Round 3: the public snapshot builder could mint loader-style seals | It is private, marks its provenance, and the step-4 evidence writer refuses a snapshot (`loader.py:842`). An object column's missing cells must be NaN, because `None` or `pd.NA` would rebuild as NaN. Invalid Unicode and parse errors refuse as `U2CohortError` | `c2f15bc` | snapshot-minting, object-column and Unicode tests |

The dry run records the round-3 refusals (`track_u2_dry_run.py:303`), and `test_u2_scripts.py` asserts each one's error class and message.

**Why every `row_set` is refused, not only unequal ones.** `U2Row` is not final, and it compares its override mappings with `==`. A row equal by value can still compute otherwise, because a subclass can override `income_spec`. A registered run therefore has one source of rows: `rows.REGISTERED_ROWS`, whose `as_dict()` the preflight binding hashes.

**Why the snapshot, not more type rules.** Each round of type rules on pandas objects closed the cases it was shown and left another open: after round 1 came `attrs` hooks, array subclasses, and Index and dtype subclasses. The snapshot closes the class rather than the cases:

- **The rule.** The run reads only frames parsed from the hashed text. If that text hashes to the frozen digest, it is the text of the frames step 4 froze, and the parse recovers their values.
- **The differential.** In the third round, a verifier ran the full registered pipeline on the same loader-sealed invented inputs twice: at `c27e46f`, which computes on the snapshot, and at `75c16d5`, which computes on the loader's frames. Both runs used the committed parameters, the same pointer and evidence, and a test-only role patch so that invented data completes. The two 667 KB outputs differ in one value only: `cohort_provenance.psid_data_dir`, which is intentionally no longer recorded. Rows, sensitivities, diagnostics, counts and tabulation are identical. The fourth pass adds `cohort_provenance.registered_snapshot: true`.
- **Legitimate loads are not refused.** The type rules and the rebuild check run at every digest, including the loader's seal and the step-4 evidence writer. A real-data frame that broke them would therefore refuse at step 4, before any registration. A test runs U1's marriage and earnings transforms on invented raw columns and digests what they build (`::test_the_inherited_readers_transforms_meet_the_type_rules`). The second round also ran the loader end to end with the unpatched inherited readers on invented staged files, including edge cases. Nothing was refused.
- **Cost.** On invented frames scaled to 100,000 rows per wave frame and 1,000,000 rows of earnings (72.6 million cells), building the snapshot took 25.5 seconds against 9.5 seconds for one digest. A registered run computes the digest 23 times, so the snapshot adds about a tenth.

### Before and after

Each case was run on invented data against the code before its fix and against the fix. The "at" commits here and in the differential below are the rebased ids. The verification ran on the pre-rebase commits `0e84127`, `c8ca02d` and `00caf93`, which are not on GitHub. Each has the same patch as its rebased commit (`77a17ce`, `75c16d5`, `c27e46f`; `git patch-id`). Their trees differ only by the master each was based on, which in U2 files is master's own `tests/track_u2/test_u2_isolation.py`.

| Case (invented) | Before | Fixed |
|---|---|---|
| Forged seal over +5 in one 2019 income cell, bound hash only (probe B2) | accepted at `cd51fcb` | refused: the record is required |
| The same forgery, with the bound record | n/a | refused: frame digest |
| U0 with the 2 percent interest override in `row_set` (probe B3) | computed at `cd51fcb` | refused before any check |
| Provenance label equal to nothing and unequal to nothing, with an altered row set | reached the rows on the first draft of the fix | refused: label |
| Record whose frame digest is a `str` subclass equal to everything | accepted at `77a17ce` | refused: not plain JSON |
| `family_wealth` as a `dict` subclass whose `get` serves other frames | accepted at `77a17ce`; a full invented run changed 138 cells | refused: plain dict |
| One `how_ended` cell that prints its own text but compares as `separated`, edited in place with no seal forgery | accepted at `77a17ce` | refused: exact `str` |
| `RoleContext.rules` rewritten with `object.__setattr__` | accepted at `77a17ce` | refused; the rows get a fresh context |
| `attrs` hooks that restore the frames before each digest and alter them after | accepted at `75c16d5`; a full invented run computed every row on invented zero incomes | refused: attrs |
| `StringArray` subclass swapping `male` and `female`; `IntegerArray` subclass adding 5 on iteration | accepted at `75c16d5`; the U0 sex cells swapped | rows read the snapshot's base arrays |
| Caller-edited `registries` and `psid_data_dir` in the inputs' provenance | recorded at `75c16d5` | the record's and committed pins'; no data directory |
| Progress callback editing the passed context's `RoleRule` objects in place | reached every row at `c27e46f` (a regression) | rows read private copies |
| A weight computed as `0.013 × 8,950,792` | refused at step 4 at `c27e46f` (false refusal) | rebuilds exactly |

### Invariants stated and tested (round 3)

17. **Bound evidence record.** A registered check accepts inputs only if all of the following hold. Otherwise it refuses.
    - The record is plain JSON data, valid, and hashes to the bound value.
    - The bound hash and the sealed hash are exactly `str` and equal.
    - The digest of the inputs' text equals the record's frozen digest.
    - Their recorded PSID file, bundle and cited-source hashes equal the record's.

    For every numeric cell of every input frame and every nonzero invented offset, a seal forged over the changed frames passes the provenance check yet refuses (`test_u2_loader.py::test_no_seal_forged_over_any_changed_cell_passes_the_registered_check`, 100 examples).
18. **Registered rows only.** Every `row_set` given to a registered run refuses before any input, parameter or row is touched (`::test_a_registered_run_refuses_every_row_set_before_any_check`, 60 examples).
19. **Check, then use.** A registered run computes only on the snapshot, the fresh read of the pinned parameter files, and a context holding private copies of the committed role rules. Nothing the caller holds reaches a row. That covers frames, arrays, `attrs`, rule objects and the progress callback; the attrs, rigged-array, callback and rule-object tests check each one.
20. **Faithful rebuild.** Every frame over the allowed dtypes whose labels are nonempty and whose text holds no NUL character rebuilds from its digested text to the same values and dtypes, with no refusal (the precondition and the whitespace fix are from the closeout; see "Round 3 closeout") (`::test_every_frame_over_the_allowed_dtypes_rebuilds_exactly`, 300 examples). The loader's and generator's frames rebuild exactly (`::test_the_snapshot_rebuilds_the_loader_and_generator_frames_exactly`).
21. **The digest pins what it reads.** The digest refuses any container, key, label, dtype or string cell outside the exact types the loader builds: a mapping subclass under any of six lying methods (40 examples), and a `str`-subclass cell in any string column (40 examples).
13. **Parameter content**: the precondition, and life-table names in the content clause (`test_u2_parameters.py::test_every_precondition_label_is_necessary`, 90 examples; `test_u2_parameters.py::test_life_table_names_are_content`).

### Conservative readings (round 3)

17. **Every `row_set` refuses in a registered run**, the registered mapping itself included (§14).
18. **No source gate in a registered run.** The run applies none, so a gate's audit would be the caller's claim. `main` passes none.
19. **The snapshot records no data directory.** The loader's `psid_data_dir` is the caller's claim and was never checked.
20. **The digest refuses empty string cells, `None` or `pd.NA` in object columns, and dtypes outside the seven the loader builds.** The CSV text writes these exactly as it writes a missing value or another dtype, so a rebuild could not tell them apart. The loader and U1's readers build none of them, so any refusal comes at step 4.
21. **The snapshot's frames have a default RangeIndex.** The digest omits the index. Relabelling every input frame's index in 24 ways (shifted, reversed, duplicated) left the full registered output unchanged in the second round.

**Limits.** These guards defend the `run_track_u2` and `check_inputs` API against caller-supplied objects. They do not defend against code that monkeypatches the runner, rebinds or mutates module state (`rows.REGISTERED_ROWS`, the cached committed role rules), or reaches private objects through `gc` or frame inspection. The verification showed that mutating `rows.REGISTERED_ROWS` in-process changes a registered run; the artifact records each row's overrides. `main` runs no caller code between its preflight and the run.

### Test results (round 3, code-final `db9725f`)

**Every `tests/track_u2` file, one per command, with `-p no:xdist`: 1,084 passed, 10 skipped, 0 failed.** The 10 skips are the registered artifact's absence.

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
| `test_u2_loader.py` | 126 passed (was 64) |
| `test_u2_mappings.py` | 55 passed |
| `test_u2_memo.py` | 14 passed |
| `test_u2_parameters.py` | 51 passed (was 48) |
| `test_u2_pipeline.py` | 27 passed, 10 skipped (was 26) |
| `test_u2_plans.py` | 39 passed |
| `test_u2_properties.py` | 17 passed |
| `test_u2_roles.py` | 71 passed |
| `test_u2_scripts.py` | 31 passed |
| `test_u2_worked_cases.py` | 14 passed |

Other runs:

- **`tests/estimates/test_birth_evidence_artifact.py`:** 13 passed.
- **The §13 U1 suite, unmodified:** 390 passed, 39 skipped, 0 failed, the same files and counts as rounds 1 and 2.
  - It ran with HOME and `POPULACE_DYNAMICS_PSID_DIR` pointed at an empty directory.
  - An audit hook refused any open, listing or scan under the real `~/PolicyEngine/psid-data` and logged any under the evidence directory and REFS. It refused and logged nothing. Its self-test refused a nonexistent probe path before any open.
- **U1 differential, rerun at `db9725f` against `9cee2423`** (fresh `git clone --shared` clones, both clean, with the hook active):
  - `all_equal` and `all_checks_passed` are true, and the dry run was not skipped;
  - the dry-run `result.json` and `RESULTS.md` are byte-equal;
  - refusal expectations are met at both commits;
  - no loader file was accessed.

  The report is committed as [`u2_m2_u1_differential_db9725f.json`](u2_m2_u1_differential_db9725f.json) (SHA-256 `6ed35e6b9e577195987e0980622ca480ccd45c0cfc8f426adb4b70011a1ffdca`).
- **Black (`-l 79`) and ruff** are clean on the 11 changed Python files.
- **Tiers** (`pytest --collect-only -q -m <tier>`, `-p no:xdist`, the hook active and never triggered):
  - unit 6,091 (+62);
  - artifact 3,540 (+4);
  - integration_psid 1,341;
  - reproduction_legacy 520;
  - oracle_policyengine 220;
  - total 11,712, equal to the full collection.
- **Isolation:**
  - No protected file changed, and `test_u2_isolation.py` passes on master's per-commit and merge rules.
  - No new source module was added, so `POST_REVIEW_SOURCE_EXCLUSIONS` is unchanged.
  - No milestone-1b-owned file was touched.

### Not done (round 3)

- **The evidence record itself**, as in rounds 1 and 2. It is written by the §20 step-4 structure pass on real data, which is separately authorized.
- **The pandas environment.** The frame digest hashes pandas' dtype names. A different pandas version or string-inference setting at the one-shot than at step 4 would therefore refuse a legitimate load. This predates round 3, and it must be pinned or recorded before step 4. It is a separate follow-up.
- **PR #524 (d1090)** changes the same U2 files. Whichever of the two lands second needs a conflict pass.
- **Independent review of this round's commits.**

## Round 3 closeout (2026-10-15 to 2026-10-16)

The round-3 lane's owner session ended on 2026-10-11 with four items open:

- the fourth-pass mutation run, whose Subfleet job (`20261011-113833-u2r3-mutation`) reached its six-hour limit without a report;
- the report's round-3 section and the exposure record, which described `db9725f`;
- the tier recount, the U1 suite and the U1 differential at the final commit;
- an independent review.

The "Microcosm dynamics" coordinator adopted PR #525 and handed it to this lane: the main session of a Claude Code session (Claude Opus 5.5, blind builder). This lane finished the four items and fixed what the closeout review and the mutation run found. Its exposure record is in [`u2_m2_exposure.md`](u2_m2_exposure.md#round-3-closeout-lane).

**INVENTED DATA - NOT A COMPARISON:** every case below is the invented population, its invented staged files or an invented frame. No real PSID record was read.

### Merge with master

`183c7ef3` merges master `9af53921` into the branch. Since the branch's last merge (`db9725fe`), master had gained #524 (Max's d1090 ruling: the B1 and B2 family-unit exclusions), #540 (the d637 registry commits, after which the loader's source preflight passes with 0 blockers) and other PRs. Three files conflicted:

- `tests/tier_counts.json` and `tests/README-tiers.md`: recounted by collection on the merged tree.
- `tests/track_u2/test_u2_loader.py`: only the docstring of `test_loaded_inputs_take_the_registered_path_only`. The merged docstring states both the round-3 record binding and #524's registry build. The body merged without conflict.

Checks on the files that merged without conflict:

- A `RoleContext` holds `RoleRule(**rule.as_dict())` copies (`sources.py:1128`). Since #524, `RoleRule.__post_init__` reads the exclusion mapping back into a `FamilyUnitExclusion` (`sources.py:783`), so the copies round-trip exactly, exclusions included. `test_u2_roles.py::test_role_rules_round_trip_through_as_dict` and `::test_registry_context_builds_as_the_declared_context` pass.
- `role_rules_text` writes each exclusion through its `as_dict()`.
- `test_u2_scripts.py`'s invented-variant list keeps #524's three appended variants.

### Closeout review

An independent review of `183c7ef3` returned **APPROVE**. It was a Claude Opus 5.5 reviewer with a shell (Subfleet job `20261015-145546-pr525-review-opus`); the Codex lanes were under an operator hold, so the GPT-6.1 Sol job was cancelled before launch. It found no blocking defect and no bypass of the registered-run binding through `run_track_u2` or `check_inputs`, and 13 of the 16 fixes it reverted made the new tests fail. Its findings:

| Finding | Severity | Resolution |
|---|---|---|
| 1. Most file:line references in the round-3 section moved with the master merge | should-fix | Updated to the code-final commit |
| 2. The "before" commits `0e84127`, `c8ca02d` and `00caf93` predate the rebase and are not on GitHub | should-fix | The section cites the rebased commits `77a17ce`, `75c16d5` and `c27e46f`, each with the same patch as its original (the trees differ only by master's base), and names the originals |
| 3. Invariant 20 is false as written: a one-column frame whose only text cell is whitespace writes a whitespace-only CSV line, which pandas drops, so the rebuild refuses the frame | informational | Fixed: `_rebuild_frame` keeps blank lines as rows (`cohort.py:697`). Invariant 20 now states its remaining precondition: nonempty labels and no NUL in the text |
| 4. No test pins that each role context holds its own `FamilyUnitExclusion` objects | informational | `test_u2_loader.py::test_role_contexts_hold_private_exclusion_objects` and `::test_exclusions_edited_from_the_callback_reach_no_row` |
| 5. Two guards cannot be reached from the public API: the births-digest check (`runner.py:719-728`) and the step-4 digest comparison (`loader.py:854-858`) | informational | Kept as backstops and described as such |
| 6. A broken anchor; invariant 13's test paths; the PR body and exposure record still at `db9725f` | informational | Fixed |

A delta review of `183c7ef3..a1858bb9` (Claude Opus 5.5 with a shell, Subfleet job `20261016-015339-pr525-delta-review`) also returned **APPROVE**. It found the four code changes correct and minimal; each only adds a refusal, except the parse change, whose result must write back the same text. Seventeen of its mutation runs failed the new tests. Its findings:

| Finding | Severity | Resolution |
|---|---|---|
| 1. The rebase note said the pre-rebase commits equal the rebased ones in every U2 file; the trees differ in master's `test_u2_isolation.py` | should-fix | The note now says each has the same patch and the trees differ only by master's base |
| 2. The U+3000 whitespace cases never failed before the blank-line fix: pandas' default parser drops only lines of spaces and tabs | should-fix | The before-and-after row drops them; the tests call them controls |
| 3. A frozen dataclass still has an instance `__dict__`, so `object.__setattr__` could shadow an exclusion's `applies` or a rule's `as_dict` behind an exact type and text (rows unaffected) | informational | Fixed in `ed82c02d`: both classes are slotted, as the review proposed and tested; `test_u2_loader.py::test_rules_and_exclusions_hold_no_instance_attributes` |
| 4. The PR body was stale and the PR conflicted with master | informational | The body is updated; master is merged at the landing slot |
| 5. The report's header named `12e1db0` as code-final | informational | Fixed |
| 6. Mutant 25's case count; the exposure JSON's wording on `test_psid_research_sources.py`; the differential note omitting the interpreter path; `e08b98dd` alone fails the tier-count check | informational | Fixed or noted below |

A confirmation review of `a1858bb9..90a658ef` (Claude Opus 5.5 with a shell, Subfleet job `20261016-034122-pr525-confirm-review`) returned **APPROVE**: slotting the two classes changes no legitimate behavior, and the new test fails with either class unslotted. Its one should-fix, a second copy of the rebase claim in the first review's table, and its wording notes (spaces and tabs, not all ASCII whitespace; mutant 25's variant; one test-id shorthand; keeping the `e08b98dd` differential report) are applied. It also noted that `RoleContext` itself is not slotted, so its `rule` method can be shadowed while `check_inputs` accepts the context; see "Not done (closeout)".

### Fourth-pass mutation run

The run that the round-3 lane dispatched (`20261011-113833-u2r3-mutation`) reached its six-hour limit with no report, so its 28 mutants were split across four Subfleet lanes (Claude Opus 5.5, one standalone clone each, at `183c7ef3`). Three new mutants probe #524's exclusions. A host restart ended three lanes before their reports, and their stream logs and progress files kept every result they had reached. Two finishing lanes ran the remaining mutants at `e08b98dd`. Each lane applied one mutant at a time, ran the U2 test files that reach it, and restored the tree. A survivor got a probe on invented data, and a test for each real gap was written, run both ways and added (`e08b98dd`, `fcfc4025`). This lane checked every added test the same way: it applies the mutant by exact string replacement, runs the test, and restores the file.

**Result: every mutant is killed at `ed82c02d`.** Six survived the tests that existed and now have killing tests: 10, 16, 20, 21, 27 and 29. Two more were killed by a message check only. Mutant 9 now has a behavioral test, and 23a's input is still refused before any row.

| # | Mutation | Lane | Result | Killing tests at `ed82c02d` (`test_u2_loader.py::` unless named) |
|---|---|---|---|---|
| 1 | `run_track_u2` computes on the caller's inputs, not the snapshot | d | killed | `test_rows_never_read_the_callers_arrays`, `test_the_snapshot_records_the_bound_records_provenance`, `test_frames_changed_after_the_check_reach_no_row`, `test_no_evidence_is_recorded_from_a_registered_snapshot` |
| 2 | `_rebuild_frame` drops the rewritten-text refusal | a | killed | `test_the_step_4_evidence_refuses_frames_that_do_not_rebuild` |
| 3 | `_rebuild_frame` drops the round-trip float parser | a | killed | `test_every_frame_over_the_allowed_dtypes_rebuilds_exactly`, `test_computed_floats_rebuild_exactly` |
| 4 | the type rules drop the `attrs` refusal | a | killed | `test_an_attrs_object_on_an_input_frame_refuses` |
| 5 | the type rules allow empty strings | a | killed | `test_the_type_rules_refuse_each_case[empty-string]` |
| 6 | object columns allow `None` and `pd.NA` | a | killed | `test_an_object_column_holds_only_nan_as_missing` |
| 7 | any NumPy dtype is allowed | a | killed | `test_the_type_rules_refuse_each_case[int32]` |
| 8, 8b | any extension dtype is allowed by `isinstance` (8b: only the two allowed classes, by `isinstance`) | a | killed | `test_an_unlisted_column_dtype_refuses`, `test_the_type_rules_refuse_each_case[category]`, `[dtype-subclass]` |
| 9 | `_plain_hashes` returns its argument unchecked | b | killed only by message; now killed by behavior | `test_a_recorded_hash_map_must_be_exactly_a_dict` (new) |
| 10 | the bundle check drops its exact-`str` rule | b | survived | `test_a_recorded_file_bundle_must_be_an_exact_str` (new) |
| 11 | the registration pointer is checked by `isinstance` | b | killed | `test_a_registration_pointer_must_be_an_exact_str` |
| 12 | a registered run accepts a source gate | b | killed | `test_a_registered_run_takes_no_source_gate` |
| 13 | `RoleRule` is not final | c | killed | `test_role_rules_are_final_and_bound_by_text` |
| 14 | contexts hold the shared cached rules | c | killed | `test_role_contexts_hold_private_rule_objects`, `test_rules_edited_in_place_from_the_callback_reach_no_row` and two others |
| 15 | a context stores the caller's rules | c | killed | `test_role_rules_are_final_and_bound_by_text` |
| 16 | `role_rules_text` drops its exact-type rule | c | survived | `test_a_lookalike_rule_context_refuses` (new) |
| 17 | `_committed_roles` does not wrap refusals as `U2RunError` | c | killed | `test_a_role_registry_refusal_is_a_run_error` |
| 18 | the step-4 writer accepts a registered snapshot | d | killed | `test_no_evidence_is_recorded_from_a_registered_snapshot` |
| 19 | the step-4 writer drops the rebuild check | d | killed | `test_the_step_4_evidence_refuses_frames_that_do_not_rebuild` |
| 20 | the snapshot takes its provenance from the caller | d | survived | `test_the_snapshot_never_reads_the_callers_recorded_hashes` (new) |
| 21 | `run_track_u2` drops the births check | d2 | survived | `test_a_snapshot_edited_after_the_check_reaches_no_row` (new; a backstop, reached only through `gc`) |
| 22 | `_frame_text` drops the Unicode check | d2 | killed | `test_invalid_unicode_refuses_as_a_cohort_error` |
| 23a | the label check is dropped from `run_track_u2` only | b | killed by message; every label is still refused before any row | `test_a_registered_run_takes_only_an_exact_provenance_label[str-subclass]` |
| 23b | the label check is dropped from both entry points | b | killed | `test_a_registered_run_takes_only_an_exact_provenance_label[rigged-equality]`, `[str-subclass]` |
| 24 | `run_track_u2` drops the row-set refusal | b2 | killed | `test_a_registered_run_refuses_every_row_set_before_any_check`, `test_a_registered_run_refuses_altered_row_definitions`, `test_u2_scripts.py::test_dry_run_records_every_branch_and_refusal` |
| 25 | `_plain_json` checks by `isinstance` | d2 | killed | `test_a_malformed_evidence_record_refuses` (with every check by `isinstance`, 2 of its 3 cases; each check alone, its own case), `test_a_rigged_digest_in_the_record_refuses` |
| 26a | `_wave_frames` accepts any mapping | d2 | killed | `test_no_frame_container_but_a_plain_dict_is_digested`; `test_a_frame_container_that_is_not_a_dict_refuses` (new) covers a non-dict mapping |
| 26b | `_wave_frames` accepts `int`-subclass keys | d2 | killed | `test_a_wave_key_must_be_exactly_int[int-subclass]`, `[bool]` |
| 27 | `check_inputs` compares the rules with `==`, not as text | c | survived | `test_rewritten_rules_with_a_rigged_field_refuse` (new) |
| 28 | the bound and sealed hashes lose their exact-`str` rule | b2 | killed | `test_loaded_inputs_take_the_registered_path_only`, `test_a_registered_run_needs_the_evidence_its_registration_binds[unnamed]`, `test_a_rigged_evidence_hash_refuses[bound]`, `[seal]` |
| 29 | contexts' copies are shallow, so they share exclusion objects | this lane | survived (also the review's M16) | `test_role_contexts_hold_private_exclusion_objects`, `test_exclusions_edited_from_the_callback_reach_no_row` (new) |
| 30 | `RoleRule.as_dict` drops the exclusion's sex | b2 | killed | seven `test_u2_roles.py` tests, among them `test_exclusions_remove_exactly_the_units_that_hold_a_trigger`; the two new exclusion tests |
| 31 | `RoleRule` accepts any object as its exclusion | b2 | killed | `test_u2_roles.py::test_role_rules_round_trip_through_as_dict` |

The step-4 digest comparison (`loader.py:854-858`; the review's M14) still has no killing test. It is a backstop behind the seal check and the rebuild refusal, as finding 5 says.

**Other findings of the mutation lanes:**

- **Fixed in `e08b98dd`:**
  - the whitespace-only rebuild (lane a, independently of the review);
  - big-endian dtypes, which passed the type rules and then crashed the rebuild with a raw `KeyError` (lane a);
  - a `FamilyUnitExclusion` lookalike, which `check_inputs` accepted (lane c).
- **Within the stated limits, not changed:** code that reaches the private snapshot through `gc` can edit it during the `progress` callback, after the births check (lane d2). The limits already exclude code that reaches private objects through `gc`, and `main` passes a fixed `print` callback. If the threat model ever widens, a registered run could also refuse a caller-supplied callback, as it refuses `row_set` and `source_gate`.
- **Test harness:** under `pytest -n`, a failure report that holds a lone surrogate (`test_invalid_unicode_refuses_as_a_cohort_error`, under a mutant) cannot cross xdist's channel and ends the run with an INTERNALERROR (lane d2). CI runs without xdist.

### Before and after (closeout)

| Case (invented) | Before | Fixed |
|---|---|---|
| One-column `str`, `string` or object frame whose only cell is `" "`, a tab or `" \t "` | refused at step 4 at `183c7ef3` (a false refusal) | rebuilds exactly |
| A big-endian (`>i8` or `>f8`) `person_id` column | passed the type rules, then raised a raw `KeyError` in the rebuild at `183c7ef3` | refused at the digest: dtype |
| A registry context whose 2015 code-20 rule holds an object that prints as the B1 exclusion but applies to nobody | accepted by `check_inputs` at `183c7ef3`; the rows were unaffected, because a registered run computes with a fresh committed context | refused: not exactly a `FamilyUnitExclusion`; the class is final |
| The same rule's exact `FamilyUnitExclusion` given an instance attribute `applies` that excludes nobody | accepted by `check_inputs` at `a1858bb9`; rows unaffected, as above | refused: the slotted instance takes no attribute |

### Invariants (closeout)

20. **Faithful rebuild**, restated. Every frame over the allowed dtypes whose labels are nonempty and whose text holds no NUL rebuilds exactly from its digested text, with no refusal. The property draws object columns too and pins the whitespace cases (`test_u2_loader.py::test_every_frame_over_the_allowed_dtypes_rebuilds_exactly`, 300 examples plus 3 explicit; `::test_a_whitespace_only_text_cell_rebuilds`, 12 cases).
21. **The digest pins what it reads**, extended: it refuses a non-native byte order, whose dtype name matches an allowed one while its written name does not (`::test_the_type_rules_refuse_each_case[big-endian-int64]` and `[big-endian-float64]`).
22. **Exact role rules.** Every rule a role context holds is exactly a `RoleRule`, every exclusion it carries is exactly a `FamilyUnitExclusion`, and both classes are final and slotted, so neither a subclass nor an instance attribute can override a method behind an exact type and text. Each context holds its own objects, so no edit of one context reaches another or a registered run's fresh one (`::test_a_lookalike_rule_context_refuses`, `::test_a_rule_holds_exactly_a_family_unit_exclusion`, `::test_rules_and_exclusions_hold_no_instance_attributes`, `::test_role_contexts_hold_private_exclusion_objects`, `::test_exclusions_edited_from_the_callback_reach_no_row`).

### Test results (closeout)

Every Python command below ran under an audit hook that refused any open, listing, scan or glob under the PSID directory, the evidence directory or REFS. HOME and `POPULACE_DYNAMICS_PSID_DIR` pointed at empty directories. The hook refused nothing.

- **The U2 files at `ed82c02d`** (every `tests/track_u2` file, `tests/data/test_track_u2_income_wealth.py`, `tests/estimates/test_birth_evidence_artifact.py` and `tests/test_legacy_manifest.py`; `-n 4`): **1,309 passed, 254 skipped, 0 failed.**
  - 244 skips are `test_psid_research_sources.py`'s documentation tests, whose PDFs are not staged under the empty PSID root, so they opened nothing. Its other 147 tests ran and passed without PSID files.
  - 10 skips are `test_u2_pipeline.py`, whose registered artifact does not exist.
- **The §13 U1 suite, unmodified, at `ed82c02d`** (the code-final commit): **390 passed, 39 skipped, 0 failed**, the same files and counts as rounds 1 to 3. `git diff 9cee2423` over the §13 list is empty. It also passed at `183c7ef3` and `e08b98dd`.
- **The U1 differential at `ed82c02d` against `9cee2423`**, in fresh standalone clones, both clean: `all_equal` and `all_checks_passed` are true, refusal expectations are met at both commits, no loader file was accessed, and the dry run was not skipped. Its report is committed as [`u2_m2_u1_differential_ed82c02.json`](u2_m2_u1_differential_ed82c02.json) (SHA-256 `d61b4a2874a590b9133c6aa9178f4a4f978d6ed75aec9f254071fc9b5414fe75`). It also ran equal at `183c7ef3` and `e08b98dd`; the report at `e08b98dd` is kept as [`u2_m2_u1_differential_e08b98d.json`](u2_m2_u1_differential_e08b98d.json) (SHA-256 `f0023ebbe6a9c8828bc18de9834de90e889c49641646b218d70449a3124fad3c`), and the run at `183c7ef3` was not kept. It differs from the round-3 report (`db9725f`) only in clone paths, heads, dates, the interpreter path and the dry run's temporary output directory, which the dry-run hashes include. Within each run, the base and the candidate agree.
- **Black 26.5.1 (`-l 79`) and ruff** are clean on the changed Python files.
- **Tiers** (`pytest --collect-only -q -m <tier>`): unit 9,047 (+91 over master `9af53921`, 29 of them added at this closeout), artifact 4,205 (+4), integration_psid 1,401, reproduction_legacy 520, oracle_policyengine 308. The total, 15,481, equals the full collection. `e08b98dd` alone fails the tier-count check, since it adds 23 tests without recounting; `a5df03c2` recounts.

### Not done (closeout)

- **The evidence record itself**, as in rounds 1 to 3. The §20 step-4 structural pass writes it on real data, and that pass needs Max's authorization.
- **The pandas environment** (carried from round 3). The frame digest hashes pandas' dtype names, so the pandas version and string-inference setting at the one-shot must equal step 4's. They must be pinned or recorded before step 4. **Closed by #544 (2026-10-16):** the pre-registration evidence record (schema v2) freezes `cohort.frame_environment()` with the digest, and `loader.check_frame_environment` refuses a frozen load or registered run under any other pandas version or string inference setting (`test_u2_loader.py::test_any_other_frame_environment_refuses_the_registered_check`, `::test_a_frozen_load_refuses_another_frame_environment`).
- **`RoleContext` is not slotted.** An instance attribute can shadow a context's `rule` method while its type, kind and rules text pass `check_inputs` (confirmation review). No row reads the caller's context: a registered run computes with a fresh committed one (`runner.py:712`), and only that context's `rule` is called (`cohort.py:1318`). Slotting it would close the shadow, as `ed82c02d` did for the rule classes; it is left as a known limit.
- **The tier recount at the landing slot.** Tiers are recounted again when the coordinator's merge slot comes up, since other PRs land first.
