# The d1408 delayed-credit diagnostic

**Verification class: labelled diagnostic.** Admitted scope is the six
retained model results authorized by ruling d1408 on 12 October 2026,
using local PSID. This is not statutory population validation, a new
registered result, a behavioral estimate, or a forecast. Registered
artifacts, configurations and evidence pins are retained unchanged.

## Method

The diagnostic calls historical input builders, claim functions, benefit
functions and model tabulators directly. It never calls a registered
one-shot entry point. Each model's recorded code commit supplies its
implementation, exported by a read-only, explicitly scoped `git archive`
into `scratch/d1408/`. The policy parameter bytes are pinned separately.
Original claim draws, expected claim distributions, payment rounding,
old-age, disability and death bases remain the historical caller's.

Section 202(w)(2)(A), 42 USC 402(w)(2)(A), ends increment months before
attainment of age 70. POMS RS 00615.692D–E supplies the cohort rates and
maximum windows. The diagnostic selects the isolated #494 reference with
`DelayedCreditWindow.STATUTORY`; its legacy check uses the original
48-month computation. The captures and their existing manifest are in
`tests/data/track_b/gross_benefit_sources/`. No new source is fetched or
introduced. Existing source-integrity and statutory-example tests remain
the conformance authority.

The flag is exactly `1917 <= birth_year <= 1942 and late_months > 48`,
or `birth_year < 1917 and late_months > 0`. Track M preserves its
whole-year entitlement convention. Claiming callers preserve their
age-70 cap. A factor evaluation is counted separately from its use in a
payment, an auxiliary basis, or an inverse-MS5 PIA.

Section 202(w)(6)(A) assigns earlier cohorts a different rate. The current
parameter bundle does not supply that statutory rate. Positive pre-1917
evaluations therefore have reason `unsupported_pre1917_credit_rate` and
no statutory amount. A legacy placeholder may remain in a supported-only
sensitivity calculation, with that limitation stated explicitly; it is
not a statutory estimate for those records. Refusals remain in admitted
denominators.

## Supported and refused computations

| Computation | Treatment |
| --- | --- |
| Historical model inputs and supported 1917–1942 late claims | Reconstruct, cross-check legacy headlines, and change only the credit window |
| Earlier-than-FRA claims and births from 1943 | Retain original behavior; differential tests cover these shared surfaces |
| Track M old-age factors | Preserve whole-year month arithmetic, including inverse-MS5 and auxiliary payment gates |
| Track M disability and death factors | Remain 1; excluded from delayed-credit flags |
| R7 linked deceased workers | Include original and shared-vector records, positive claim-PMF mass and beneficiary weights |
| Cost ordering's R7 component | Include its baseline denominator and 1b model cost ratio; evaluate 1a separately |
| First-estimates exact projected ledgers without pinned fitting dependencies | `historical_projection_dependencies_unavailable`; report unverified support bounds and expected counts, no actual counts or headline amounts |
| Positive pre-1917 credits | `unsupported_pre1917_credit_rate`; no statutory amount |
| Fewer than ten underlying people | `<10` for the whole cell, including weights, shares and changes |
| Overlapping subtotal revealing a small complementary group | `suppressed_complementary`, including the subtotal's weight and changes |
| Restricted files, comparator fields and external benchmark changes | Refused; no benchmark is needed or reported |

## Invariants and executed tests

The following method tests use invented inputs. Hypothesis properties
execute the variable-input invariants; fixed examples pin the boundary,
unsupported and API cases. They do not validate a population
claim. The publication fixture names the six authorized artifact paths
but never reads those artifacts. The repository's static tier policy
therefore classifies its thirteen cases as `artifact`; the other seventy-two
cases are `unit`. There are eighty-five cases across nine modules.

### Shared convention and accounting

These tests are in `tests/test_d1408_common.py` (eighteen cases).

| Invariant | Exact tests |
| --- | --- |
| The flag equals the strict supported-cohort `late_months > 48` region and the separate pre-1917 positive-month region; negative months, 48, 1917 and 1943 retain their boundary meanings. | `test_flagged_region_is_exact`, `test_flagged_region_boundaries` |
| The statutory wrapper equals the isolated #494 reference on its supported surface, including unchanged later cohorts and early claims, with zero additional numerical tolerance. The original function is restored. | `test_statutory_differential_matches_isolated_reference` |
| The legacy wrapper equals the original calculation for every generated input and restores the original function after an exception. | `test_legacy_context_is_identical_and_restores_on_failure` |
| Positive pre-1917 inputs retain only the expressly labelled legacy placeholder; the statutory reference refuses them under section 202(w)(6)(A). | `test_pre1917_is_only_a_legacy_placeholder` |
| Every quantity of a positive one-through-nine-person cell is suppressed together. | `test_small_cell_suppresses_every_quantity` |
| Each distinct person contributes weight once; duplicate calls and reversed input order preserve people, worker-record count, summed weight and the full-denominator share. Repeated evaluation is deterministic. | `test_aggregate_deduplication_order_independence_and_weight_identity` |
| Empty groups publish zero counts, weight and share while retaining the admitted denominator. | `test_empty_group_stays_in_denominator` |
| Every prohibited path word is refused case-insensitively in any path position; a permitted model-code path remains permitted. | `test_restricted_path_names_are_refused`, `test_restricted_names_are_refused_in_any_path_position` |

### Publication and assembly

These tests are in `tests/test_d1408_diagnostic.py` (five cases) and
`tests/test_d1408_diagnostic_privacy.py` (thirteen cases).

| Invariant | Exact tests |
| --- | --- |
| Nested identifiers are refused through dictionaries and lists, including null-valued identifier, individual-amount and microdata fields. | `test_nested_record_identifiers_are_refused`, `test_publication_rejects_nested_identifier_fields` |
| Nested aggregate counts at or above ten and ordinary aggregate changes remain admitted. | `test_aggregate_counts_and_suppression_are_admitted` |
| Positive numerical people counts from one through nine are refused for all tested affected, receiving and worker-person aliases. | `test_publication_rejects_unsuppressed_small_people` |
| A small group cannot publish its weight, share or change while hiding only its count; complete suppression is admitted. | `test_publication_rejects_partial_small_cell_suppression`, `test_publication_accepts_complete_small_cell_suppression` |
| An aggregate scalar record count of zero or at least ten is admitted; record lists and dictionaries are refused at every generated nesting depth. | `test_publication_accepts_scalar_aggregate_record_count`, `test_publication_rejects_record_collections` |
| A public admitted population of at least ten keeps its denominator beside a suppressed changed-person subgroup. | `test_suppressed_changes_keep_public_admitted_denominator` |
| Exactly the six ruling-authorized artifact identities appear once. Their order, repeated validation and input objects are unchanged. Duplicates and every incomplete subset refuse assembly. | `test_result_scope_accepts_authorized_permutations_without_mutation`, `test_result_scope_rejects_duplicate_replacing_required_result`, `test_result_scope_rejects_every_incomplete_authorized_subset` |
| Published PSID reads are relative to the PSID root (`psid-data/...`), never a home directory; an absolute read outside the root refuses assembly. | `test_psid_reads_publish_relative_to_the_psid_root`, `test_psid_reads_outside_the_root_are_refused` |
| A projection result states zero pre-1917 flags only when it emits no `unsupported_pre1917` cell. | `test_projection_pre1917_states_zero_only_without_unsupported_cells` |
| Both projection results must certify a completed membership audit, deletion of temporary memberships and a nonempty method. The actual assembler refuses publication otherwise, including a missing audit or projection result. The default launcher completes the publication audit before assembly. | `test_assembly_requires_completed_projection_privacy_audit` |

### First-estimates support bounds

These tests are in `tests/test_d1408_first_estimates.py` (thirteen cases).
Bounds and conditional expectations are separate from realized counts.

| Invariant | Exact tests |
| --- | --- |
| The strict 48-month boundary admits only age 70 on the registered age-62-through-70 PMF for supported births and FRA-month inputs. | `test_window_support_uses_strict_48_month_boundary`, `test_window_support_is_only_age70_on_registered_pmf` |
| Production-ineligible pre-1917 and post-1942 cohorts contribute no changed-window support. | `test_window_support_excludes_production_ineligible_cohorts` |
| Expected changed mass retains every unaffected age in the full PMF denominator and equals the assigned changed-age probability (absolute tolerance 1e-12). | `test_expected_mass_keeps_unaffected_probability_in_denominator` |
| Expected mass is in [0, 1], deterministic and invariant to a matching permutation of ages and probabilities; it agrees with the registered changed-age probability to 1e-12. | `test_expected_mass_is_bounded_and_order_independent` |
| Complete stock replay requires exposure strictly above every support age, is order independent, and cannot replay empty support. | `test_stock_replay_requires_strict_complete_support`, `test_empty_stock_support_cannot_be_replayed` |
| A small complementary group withholds the entire overlapping replay subtotal, while preserving the source object and deterministic output; zero and complements of at least ten remain unchanged. | `test_small_complementary_cell_withholds_replay_subtotal` |
| Mismatched lengths, negative, non-normalized, NaN and infinite probability inputs refuse before a support result, including for unsupported birth cohorts. | `test_invalid_distribution_refuses_before_computing_mass` |

### Minimum-benefit accounting

These tests are in `tests/test_d1408_minimum.py` (seven cases).

| Invariant | Exact tests |
| --- | --- |
| Late months equal twelve times whole-year age minus original FRA months. Only old-age bases enter supported or pre-1917 flags; disability and death bases remain excluded. | `test_whole_year_months_and_basis_exclusion` |
| Track M retains its original whole-year delay after age 70 when flagging, rather than silently imposing a claiming cap. | `test_track_m_keeps_delay_after_age_70_for_flagging` |
| Own and linked beneficiary associations are unique and order independent; repeating a link does not add people and an unrelated worker adds none. | `test_dependents_deduplicate_and_ignore_input_order` |
| Recipient weights and associated worker-record weights use the same admitted beneficiary frame, with the full denominator. A small person or worker-record count suppresses the entire cell; reversing input order changes nothing. | `test_weight_accounting_and_worker_cell_suppression` |
| A small linked subgroup prevents release of the complementary owner subtotal. A small cross-reading membership difference suppresses sensitivity counts and preserves the scored reading and zero headline change. | `test_complementary_suppression_protects_linked_subgroup` |
| Model shares follow the original evaluation path exactly. Changes retain admitted counts and weights; changed groups below ten suppress all count, weight and percentage-point changes together; zero and ten remain admitted. | `test_exact_share_path_and_small_change_suppression` |
| Survivor use requires the original strictly positive paid excess after the deceased-worker factor; equality and a nonpositive excess contribute no paid flow. | `test_strict_survivor_flow_matches_original_positive_excess` |

### Projection headlines and attribution

These tests are in `tests/test_d1408_projection.py` (eight cases) and
`tests/test_d1408_projection_smoke.py` (two invented adapter cases).

| Invariant | Exact tests |
| --- | --- |
| Identical finite statistics have zero change. None, NaN and either infinity remain explicitly undefined under each convention rather than becoming a zero amount. | `test_identical_headlines_have_zero_change` |
| Every defined change is statutory minus legacy. Nested labels remain, and unchanged nested values are omitted. | `test_numeric_headline_change_is_right_minus_left`, `test_nested_headlines_preserve_labels_and_omit_unchanged` |
| Only the two committed model-statistic families are selected; record cells and benchmark fields are excluded. The committed floor mean, SD, minimum, maximum and seed count remain, while individual floor-seed values are excluded. | `test_headline_selector_excludes_record_and_benchmark_fields`, `test_model_selector_includes_committed_floor_summary` |
| A hidden positive age cell suppresses every positive large age subtotal and its money change, including a second large subtotal. Empty cells remain zero. Small directed changed-person differences between rows suppress both overlapping row totals, including physical identities in different anchor waves. | `test_model_selector_includes_committed_floor_summary` |
| Checkpoints round-trip values and exact read-audit sets; code-commit or result-kind mismatches refuse reuse. Registered and committed artifact identities must agree. Final publication preserves aggregate payloads and deletes both membership ledgers and retained/replay backups before either completion certificate is written; missing ledgers refuse finalization. | `test_checkpoint_round_trip_and_read_audit` |
| Opening-stock adjustments retain the original worker and dedicated adjustment role, and are not mislabelled as a PIA lookup. | `test_opening_stock_factor_keeps_original_worker_and_role` |
| The observer returns the exact original payment objects and restores patched methods. Only a strictly positive payment whose final factor still contains the credit enters a positive role. An undone factor does not; a spouse PIA-only lookup is labelled as an unused factor. | `test_payment_observer_preserves_returns_and_tracks_positive_used_credit` |
| Row admission requires the original baseline-beneficiary flag and a positive baseline benefit. Distinct-person and mean-draw weights use that frame. Cached row attribution stays in its current anchor wave and restores row context. | `test_payment_observer_preserves_returns_and_tracks_positive_used_credit` |
| A small associated-recipient complement suppresses positive-worker person, record, weight and share aliases in both row and wave summaries, even when the worker-record complement is empty. | `test_payment_observer_preserves_returns_and_tracks_positive_used_credit` |
| Both original invented COLA and FRA adapters preserve draw indices, row definitions, benefit paths and model-tabulator APIs under both credit conventions. Restored cohort/projection instances preserve every frame, fingerprint, provenance, draw and audit. Row attribution stays in its own wave, and real readers and public writers are forbidden. | `test_invented_projection_benefit_rows_and_headlines` |

### Earnings-sharing and cost ordering

These tests are in `tests/test_d1408_sharing.py` (thirteen cases).

| Invariant | Exact tests |
| --- | --- |
| Only selected original model AST nodes execute; module prose, unrelated constants and entry points do not. Selected computations retain identical ASTs and results. | `test_selected_nodes_exclude_nonmodel_execution`, `test_selected_model_node_preserves_computation` |
| Reusing a paired historical dependency closure requires byte identity of every imported source; a changed byte refuses reuse. | `test_imported_source_identity_requires_identical_bytes` |
| Repeated calls deduplicate flagged evaluations, retain original worker/recipient/stage/basis/role attribution and exclude unchanged boundaries. Context restores after normal or exceptional execution. A flagged call without worker attribution refuses. | `test_trace_repeated_calls_are_order_independent_and_deduplicated`, `test_trace_context_restores_after_exception`, `test_trace_refuses_unattributed_flagged_credit` |
| Recipient people and original/shared worker bases deduplicate separately. Recipient weights use the full admitted denominator; worker weights do not invent a recipient-frame share. | `test_trace_group_counts_unique_recipients_and_worker_bases` |
| Positive small recipient and worker groups withhold all count, record, weight and share fields; headline changes also withhold a small affected group. Ten affected people reach model computation. | `test_trace_group_suppresses_entire_small_cell`, `test_headline_changes_suppress_all_small_affected_groups`, `test_headline_changes_admit_ten_affected_people` |
| Legacy model quantities must equal the committed model headlines exactly at original precision; a mismatch sets both reproduction and counts to unverified. | `test_exact_cost_cross_check_detects_changed_headline` |
| Unsupported placeholders preserve dataframe dtypes, admitted identities and order, while leaving every supported amount unchanged. | `test_unsupported_placeholders_preserve_dtypes_and_denominator` |
| A hidden sex subgroup withholds the opposite-sex subtotal and changes, preserving empty groups and existing small markers. Applying suppression again changes nothing. | `test_complementary_sex_suppression_withholds_count_and_changes` |

### Cross-result publication

These tests are in `tests/test_d1408_projection_publication.py` (six
cases). The pure `scripts/d1408_projection_publication.py` helper reads
no file and returns no membership identities. Temporary membership
ledgers are deleted before the assembler's completion gate is satisfied.

| Invariant | Exact tests |
| --- | --- |
| The minimized released ten-versus-eleven-person overlap withholds all implicated FRA counts, weights, shares, positive changed-row counts and age money. | `test_minimized_cross_result_residual_is_withheld` |
| Every one-through-nine person residual in either direction, including overlapping physical identities in different anchor waves, suppresses the count, weight, share and change together, while COLA, both ledgers, admitted denominators, zero/undefined cells, existing small markers and reproduction checks remain unchanged. | `test_small_people_residual_masks_counts_weights_shares_and_changes` |
| A one-through-nine worker-record residual receives the same suppression even when the associated person memberships are identical. | `test_small_worker_residual_masks_even_when_people_are_identical` |
| Identical memberships and directed residuals of at least ten retain their public quantities. | `test_equal_memberships_and_residuals_at_least_ten_remain_public` |
| A small changed-row person residual suppresses its associated wave-count aliases even when the total factor membership is identical. | `test_changed_row_residual_also_masks_wave_count_aliases` |
| Matching ledger order permutations, repeated evaluation and a second suppression pass preserve identical output; protected inputs remain unchanged. | `test_cross_result_publication_is_deterministic_order_independent_and_idempotent` |

The diagnostic's handoff reports, kept with the run evidence outside the
repository, record exact commands, pass counts and deliberate one-line
mutation failures. Mutations are restored or run in isolated scratch copies and
never retained in the implementation. Current aggregate findings remain
subject to each result's explicit legacy-headline reproduction check.

## Findings

Results and legacy-headline reproduction checks are recorded in
`docs/errata/2026-10-11-delayed-credit-window-diagnostic.json`. Counts from
a reconstruction that does not reproduce the retained headlines are
explicitly unverified. Bounds are not realized counts. Worker weights
outside the admitted recipient frame are not divided by recipient-frame
weight and described as a population share.

Track M reproduces all 96 retained model cells and 91 PSID input-file
hashes. Its supported window change leaves every committed model share
unchanged, including the inverse-MS5 paths. The aggregate erratum gives
the counts and weights, with small auxiliary cells suppressed.

The R7 audit incidentally exposed embedded benchmark fields in a retained
model artifact and in its model script while locating metadata. Those
fields are not used in reconstruction or reporting. No restricted
comparator path was intentionally opened. The report records this
exposure rather than claiming an unqualified blind audit.

## Worked examples and source findings

No new SSA monetary worked example is introduced. The isolated #494
reference's existing capture, rule-text, figure and SHA-256 checks are
run separately. No new statutory ambiguity or source erratum is claimed.
This diagnostic retains every historical rounding convention, including
intended departures from a complete statutory payment assembly.

The retained POMS RS 00615.692C example has PIA $1000.00 and 30
credits at 7/12 of 1 percent per month. It produces $175.00 in credit
and $1175.00 before whole-dollar rounding, with payment $1175.
`test_poms_692_worked_example_reproduces_175_credit_and_1175_benefit`
executes both the float reference (fraction tolerance 1e-12) and G's
exact-fraction result. Its figures and rule text remain pinned verbatim
to the existing manifest capture; this is an invented statutory check,
not a diagnostic amount for a PSID person.

## Not in scope

No registered artifact rerun, replacement, recalibration, upstream
parameter edit, new claim-age behavior, comparator, or revision of a
forecast or evaluation verdict. No person identifiers, record-level
rows or individual amounts are published. Temporary real-data rows are
kept in memory or diagnostic scratch only and removed before handoff.
