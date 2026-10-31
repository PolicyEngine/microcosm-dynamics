# Track B R2: the retirement earnings test ledger

**Verification class: statutory conformance. Admitted scope: retirement
earnings test rule mechanics on invented record-years and published
statutory worked examples. No population, behavioral or forecast claim.**

**Status: build-only, R2 part (b) revised 2026-10-23 following ruling
d1802; prior R2 review and the G v2 shared boundary remain in force.
No real-data computation.** The single-record ledger now calls G for
deduction-before-reduction readjustment when monthly statutory and
household inputs are supplied (Act 203(a)(4); RS 02501.155A.3–4).

The approved Track B design, revision 3, defines R2 in §3.1 as the
`apply_ret_year` ledger: entitlement, provisional suspension, final
deduction, grace year and family-record order. Sections 5.4 and 6 require
exact 1/2 and 1/3 rates, whole-dollar excess floors, the qualifying
divorced-spouse exception, chronological charging and explicit refusals.
Max's ruling d515 chose a Python statutory reference. This implementation
makes no Axiom or population conformance claim.

- Code: `src/populace_dynamics/track_b/ret_ledger.py` and
  `src/populace_dynamics/track_b/ret_grace.py`.
- Tests: `tests/test_track_b_ret_ledger.py` covers examples, boundaries,
  input validation, readings and refusals;
  `tests/test_track_b_ret_ledger_properties.py` executes Hypothesis
  invariants and R1 differentials; `tests/test_track_b_ret_grace.py`
  exercises carried state, all published grace examples and properties;
  `tests/test_track_b_ret_grace_differential.py` compares full invented
  histories with `tests/track_b_ret_grace_reference.py`, an independent
  test-only implementation of the captured grace rules;
  `tests/test_track_b_ret_ledger_readings.py` checks the ledger money
  consequences and properties of simultaneous RIB/DIB readings;
  `tests/test_track_b_ret_ledger_sources.py` pins source bytes, quotations
  and monetary worked examples; `tests/test_track_b_ret_ledger_deductions.py`
  covers binding maximum readjustment, household timing and R3 credits.
- Source helper: `tests/track_b_ret_ledger_support.py`.
- Captures: `tests/data/track_b/ret_ledger_sources/`. The manifest records
  the URL, UTC retrieval time, byte count and SHA-256 of each capture,
  with POMS transmittals and page dates. R1's full Act 203 capture remains
  at `tests/data/track_b/ret_sources/ssa_act_203.html`.

## Input boundary and threat model

Every public argument and declaration field has a declared schema. The
boundary admits only the declared built-in scalar kinds by exact type
(`bool` is not `int`), canonical enum members by identity, exact registered
declaration classes, and exact built-in containers of the declared shape.
Every nonmapping collection declares ordered-sequence or membership
semantics. Ordered fields and arguments admit `tuple` and `list` only,
normalizing every element into a tuple in its original order. Membership
slots admit `tuple`, `list`, `set` and `frozenset`, normalizing into a
frozenset after every raw element passes its schema. Exact monetary
encodings become built-in `Fraction` values. Dates remain exact `date`
values, and sealed result slots require the declared result layer and an
unchanged seal. A callback slot is checked with `callable()` and retained
without reconstruction; its return still requires its layer's sealed
result. Callable dataclasses therefore remain valid callbacks.

An evaluator verifies provenance: the result was computed by its own
Track B layer, has an unaltered declared payload, and has the right layer
and type. It does not verify freshness or attribution. A callback may return a genuine result
computed earlier or re-raise a genuine refusal computed earlier. The former
counts as supported; the latter counts with its own reason. Which family
receives that attribution is the caller's declaration, like its key and
weight, neither of which the evaluator can independently verify. Track B
guarantees that only values it computed enter denominators and every value
entering its functions passes its schema.

The boundary checks every raw key, value and element before reconstruction
or hashing. A mapping must yield exactly its length in distinct valid
keys. Keyed monetary histories and shares retain their associations in
dictionary snapshots; normalized-key collisions are input errors. Unknown
objects, scalar or container subclasses, forged enum values,
`__class__` spoofs and arbitrary iterators are input errors before a
coverage refusal or denominator row. Built-in mutable containers are
snapshotted per call. Their later mutation cannot change admitted results.
The boundary does not cache validation by input identity. Private internal
helpers consume the owned snapshot without re-entering public validation.
R1's generated parameter mapping proxies are accepted only around exact
built-in dictionaries and their fields receive the same schema checks.
The Hypothesis regression
`test_r2_r3_snapshot_each_parameter_bundle_once_per_public_call` executes
the one-parameter-snapshot invariant for R2, ARF and a multi-year
recomputation fold. Its monetary inputs and fold lengths vary; no public
entry reuses a cached input identity. The same property requires zero
internal calls to public declaration constructors in R2, ARF, recomputation
and grace-year computation. Private construction retains the original
domain checks while skipping the public schema walk on owned values.

This contract concerns callers using the public API. It does not claim
protection from code reaching private implementation names, monkeypatching modules, or
mutating an input from another thread during a call. Sealed result
identities and statutory cross-field identities remain checked when results
are produced or consumed. No amount, supported refusal or statutory example
changes for previously admitted ordered list/tuple and membership inputs.
Rejecting `set` and `frozenset` in ordered slots is an explicit
representation narrowing, like the earlier iterator narrowing. A set
cannot declare the order or multiplicity of events, monthly arrays,
history rows or denominator observations.

The shared external `SSAParameters` declaration retains its exact built-in
integer, float and text encodings, as the prior boundary did. Its numeric
leaves must still be finite and its field shapes must match the schema;
consumed monetary values use exact `Fraction` arithmetic. Decimal and
Fraction objects are detached. This representation compatibility does not
admit subclasses or custom scalar behavior.

Call-layout caches hold signature metadata only: positional counts, keyword
names and declared defaults. They never retain supplied values. A schema-wide
Hypothesis differential compares positional, keyword, mixed and omitted-default
calls with Python's signature binding, including missing, duplicate and unknown
arguments. Reusing a layout with fresh values must use the new values. These
checks are in
`test_every_public_argument_and_declaration_field_declares_a_schema`.

Private derived declarations and field replacements invoke their original
initializers, retaining domain checks without re-entering the public schema.
The G snapshot property and
`test_r2_r3_snapshot_each_parameter_bundle_once_per_public_call` assert zero
public declaration-constructor calls inside family, RET, ARF, recomputation
and grace computations after their input fixtures have been built. A
deliberate return to a public constructor fails these checks.

`test_all_valid_public_argument_controls_still_compute` checks each public
function and guard method against valid controls while counting schema
entries. Each call enters its public argument schema exactly once; internal
guard evaluation and date formatting use private helpers. The same property
checks invalid-date and out-of-order errors and an unknown-history refusal:
errors leave no denominator row, while a legal refusal retains one row.
Callbacks in this check return precomputed sealed results so separate public
calls made by user callback code do not count as internal revalidation.

Every public reader of a registered declaration, sealed value or stateful
guard, including a property getter called through `fget` and reachable
methods and dunders, checks its exact registered receiver
and argument schemas before attribute access or protocol use. Seal
validation starts with the exact-type check. Foreign receivers and
arguments whose hooks raise a genuine refusal produce `InvalidFamilyInput`
with zero hook calls and zero denominator rows. Genuine sealed results
still undergo seal checks. The five savings-clause guard getters retain
their valid values and one receiver-schema entry per getter.

The four-layer tests in
`tests/test_track_b_gross_benefits_fix_round_15_receivers.py` execute
`test_review_four_layer_getter_rejects_receiver_before_any_hook` and the
Hypothesis `test_every_public_reader_rejects_foreign_receiver_without_hooks`.
`test_evaluator_accepts_precomputed_genuine_result_with_declared_metadata`
and `test_evaluator_counts_reraised_genuine_refusal_with_its_own_reason`
pin the two permitted caller-composition behaviors. This closes the
receiver hook path without imposing an unverifiable freshness or family
attribution condition.


The reader boundary also covers exact registered objects whose public
fields were altered after construction. Generated representation, equality,
ordering and hash readers validate the receiver's current declaration or
seal before using those fields. Refusal seals include exception `args`,
which Python's string and representation methods consume. Direct public
`__post_init__` calls revalidate their fields; an internal initialization
marker only avoids repeating the same work during a checked constructor
and is removed when that constructor returns or raises. This marker is
not a freshness or attribution check.

Integrity covers the declared computation and refusal payload, including
exception `args` consumed by string and representation readers. Undeclared
instance attributes on sealed values are input errors, including those
that shadow registered methods; otherwise an unchanged monetary payload could invoke a
caller-supplied `items` or `__reduce__` hook. Permitted exception notes must
be an exact list of exact strings. Notes, traceback and context bookkeeping
do not determine statutory money or the counted refusal reason and do not
establish freshness or family attribution.
Raw keyword names must be exact strings before named-argument binding or
keyword lookup, including unbound readers and direct constructors.

These reader guards cover the registered G/R2/R3 declarations, computed
results, refusals, outcomes, denominator and stateful savings guard.
Imported standard-library APIs and external R1/SSA classes are not newly
wrapped. Their data pass the appropriate declared schemas when entering
the statutory layer. Public method identity belongs to this callable
boundary even when the method is not a declared monetary field.
Canonical enum tokens are checked by identity at statutory boundaries.
Inherited standard-library `Enum` factories and introspection remain
caller-side composition, like imported `Fraction` or `dataclass`
machinery; they are not alternative statutory evaluators. This reader
contract does not cover every attribute imported into a module.
This does not admit foreign enum classes as statutory reader arguments:
those must reject before enum-member iteration or other class hooks.

Public class metadata methods validate the class receiver and arguments
before lineage or typing operations. Foreign metaclasses are rejected
before descriptor hooks, including a custom `__mro__` descriptor.
Ordinary subclass definitions and generic aliases remain usable; the
existing exact-type admission rule still rejects subclass instances.

Direct declaration reinitialization rejects instance method shadows before
its generated initializer can dispatch `__post_init__`; inert extra
declaration metadata remains usable. Public dunder writers, including
`__notes__` and `__dict__`, validate values before assignment. Extra
post-init arguments are checked before field reads, and recursive
reader mappings produce `InvalidFamilyInput` without a denominator row.
Stored instance-dictionary keys also require exact built-in strings
before attribute lookup. A string subclass stored under a field or
method name can otherwise execute its equality hook inside Python’s
dictionary lookup, even when the receiver and requested name have
the correct types. This rule covers declaration snapshots and public
attribute readers on declarations, sealed values and the stateful guard.

| Additional boundary invariant | Executing test |
| --- | --- |
| Every reader argument rejects foreign values before hooks | `test_public_reader_arguments_reject_foreign_values_before_hooks`; Hypothesis `test_public_reader_argument_schema_property` |
| A nested evaluator rejects a foreign callback result before its `__class__` hook can raise a genuine refusal | `test_nested_evaluator_rejects_foreign_callback_result_without_class_hook` |
| Generated sealed and declaration readers check altered public fields before hooks | `test_sealed_reader_checks_mutated_fields_before_hooks`; `test_declaration_reader_checks_mutated_fields_before_hooks` |
| Refusal string/representation readers bind exception arguments to their seal | `test_refusal_reader_seal_covers_exception_arguments` |
| Direct public post-init calls revalidate declarations and sealed results before field hooks | `test_direct_post_init_revalidates_declaration_before_collection_hooks`; `test_direct_post_init_revalidates_sealed_result_before_field_hooks` |
| Direct construction rejects foreign constructor arguments before hooks | `test_public_new_rejects_foreign_constructor_argument` |
| Reader and constructor keyword names reject string subclasses before binding, comparison or formatting hooks | `test_public_reader_keyword_names_reject_before_binding_hooks`; `test_public_constructor_keyword_names_reject_before_binding_hooks` |
| Shadowed instance methods cannot execute through sealed serialization or mapping readers | `test_sealed_serialization_readers_reject_instance_method_shadowing`; `test_sealed_mapping_comparison_rejects_instance_method_shadowing` |
| Generated keyword names and unexpected sealed instance attributes reject before hooks | Hypothesis `test_keyword_names_and_instance_shape_reject_before_hooks` |
| Public class metadata readers check foreign receivers, arguments and keyword names while retaining valid alias/subclass behavior | `test_public_class_readers_reject_foreign_receivers_arguments_and_keywords`; `test_valid_class_metadata_hooks_keep_generic_alias_and_subclass_behavior` |
| Foreign metaclasses with raising or lying descriptors reject before class-lineage hooks | Hypothesis `test_class_metadata_rejects_foreign_metaclass_before_descriptor_hooks` |
| Every ordinary public argument and declaration field rejects foreign values before hooks | `test_every_public_argument_rejects_genuine_refusal_hooks`; `test_every_declaration_field_rejects_genuine_refusal_hooks` |
| Extra direct post-init arguments reject before field reads | Hypothesis `test_public_post_init_rejects_extra_foreign_arguments_before_field_reads` |
| Public dunder writers check foreign values before hooks | Hypothesis `test_public_dunder_writers_reject_foreign_values_before_hooks` |
| Recursive reader mappings reject as input errors with zero denominator rows | Hypothesis `test_public_reader_rejects_cyclic_mapping_as_invalid_input` |
| Direct declaration initialization rejects method shadows while retaining inert extra metadata | Hypothesis `test_public_declaration_init_rejects_instance_method_shadowing`; `test_direct_declaration_init_preserves_inert_extra_metadata` |
| Stored instance-dictionary keys reject before snapshot, reader or initializer lookup hooks, including external and nested declarations | Hypothesis `test_public_attribute_dictionary_keys_reject_before_lookup_hooks` |
| Foreign enum classes reject before metaclass iteration; registered canonical members remain usable | Hypothesis `test_foreign_enum_rejects_before_metaclass_iteration`; `test_reader_enum_schema_rejects_foreign_enums_and_keeps_canonical_members` |
| Exact integer dime-validation checks preserve the prior Fraction comparison and multiplication decisions | Hypothesis `test_dime_validation_matches_legacy_fraction_arithmetic` |
| Constructor introspection preserves the full declared initializer signature, defaults and displayed form while runtime keyword validation remains guarded | Hypothesis `test_every_public_argument_and_declaration_field_declares_a_schema` |
| Newly guarded inherited exception and mapping readers have exact public-member and argument inventories and retain valid behavior | `test_public_api_has_no_unclassified_name_field_or_argument`; `test_cross_layer_public_names_and_members_have_explicit_audit_coverage`; Hypothesis `test_all_valid_public_argument_controls_still_compute` |
| Exception note writes validate an exact list of exact strings before preserving its identity, so Python add_note appends to the stored list; later reads revalidate notes | Hypothesis `test_all_valid_public_argument_controls_still_compute`; Hypothesis `test_public_dunder_writers_reject_foreign_values_before_hooks` |
| Public calls retain their once-only argument-schema boundary; trusted private helper aliases unwrap every public guard layer | Hypothesis `test_all_valid_public_argument_controls_still_compute`, retaining its unchanged `assert not repeated` |

Performance optimizations retain the same schemas and seal checks.
Cached identities, reader flags and field names describe registered
classes; no caller value or validation result is cached. Dime validation
uses equivalent exact integer checks, pinned against the prior Fraction
comparison and multiplication by the property above, including large
signed numerators and positive denominators.
The `OwnBenefit`, `Beneficiary` and `WorkerRecord` post-init bodies
read their already-validated fields directly after their existing
field-validation step. Public constructor and post-init wrappers,
stored-key checks, field schemas, domain checks and normalization
order remain in force. The altered-field, direct-post-init, stored-key
and constructor-shadow regressions execute those boundaries; existing
family-total, proportional-share and beneficiary-order properties
cover the unchanged computation.

These tests use invented values and genuine earlier refusals only. They
assert `InvalidFamilyInput`, zero foreign hook calls and zero denominator
rows. Each adversarial callback attempts the reader and then returns a
genuine computed result if that reader silently succeeds. A scalar reader
return therefore cannot make the evaluator hide a permissive reader. The
completion report records the executed and reverted deliberate mutations, including the exact changes and failing test names.

### Collection inventory and round-15 invariants

| Slots | Kind and reason |
| --- | --- |
| `WorkEarnings.wages`; `RETBeneficiary.benefit_types`, `gross_rates`, `original_rates`; `grace_year.months` | Ordered twelve-month arrays. Position identifies the calendar month; repeated equal values remain twelve entries. In particular, `benefit_types` is a monthly array, not role membership. |
| `RecordYear.beneficiaries`; `grace_year.termination_events` | Ordered declarations and dated events. Preserve every element so duplicate identities and contradictory histories still reach their validation. |
| `count_ret_outcomes.outcomes`; `weighted_ret_total.outcomes` | Ordered observations. Preserve every row and its duplicate-key checks; distinct keys retain every count, weight and payment contribution. |
| `WorkEarnings.self_employment_months`, `substantial_service_months`; `RETBeneficiary.entitled_months`, `divorced_months`, `deemed_child_age_18_months`, `own_work_exempt_months`; `RecordYear.family_maximum_binding_months`, `other_deduction_months` | Month membership. Exact integers identify months 1 through 12; repeated declarations of a month do not create an additional month. |
| `GraceMonth.entitled_types`, `received_types`; `GraceYearState.previous_entitled_types`, `previous_section_202_types` | Membership of canonical benefit-type enums. Grace rules test which types are present, never how many times each was supplied. |
| `GraceYearDecision.kinds`, `met_eligible_months`, `protected_months`; values of `RETLedger.crediting_months` (computed outputs) | Membership of canonical grace kinds or exact months; no amounts are stored in these sets. |
| `RETLedger.months`, `workers` (computed outputs) | Ordered monthly and worker rows. Every computed row is retained. |
| R1 `ParameterValue.sources` admitted through a parameter schema | Ordered source records, preserving every declared source identity rather than silently deduplicating provenance. |
| `partial_payments.rates`, `original_rates`; R1 `ProjectionInputs.nawi`, `december_cola_percent` and `RETParameters.years`; computed `PartialPaymentAllocation.shares`, `RETLedger.crediting_months`, `reconciliation` | Keyed associations. Exact dictionary keys and every value are checked; normalization may not collapse keys. Computed immutable views retain the same associations. |

No membership field stores earnings, benefit rates, weights or dated
events. Exact integer admission rejects `True`, `1.0`, `"1"`, Decimal and
Fraction month aliases before deduplication. Enum membership accepts only
the canonical members. Repeating an admitted month or flag is therefore
the same statutory assertion, with no lost money or changed refusal.
The rules that use those memberships remain Act 203(f), CFR 404.435-.440,
RS 02501.030 and RS 02501.140; this revision changes representation only.

The shared tests in
`tests/test_track_b_gross_benefits_fix_round_15_collections.py` execute
`test_every_collection_schema_declares_order_or_membership`,
`test_every_collection_field_has_canonical_container_semantics`,
`test_every_public_collection_argument_preserves_its_declared_semantics`,
`test_membership_fields_contain_only_months_or_canonical_flags`, and
`test_membership_numeric_aliases_are_rejected_not_collapsed`.
Hypothesis `test_denominator_sequences_preserve_duplicate_key_errors` verifies
that duplicate keys remain input errors in all four layers; a single row
retains its count and weight. Every ordered field rejects both set forms instead of silently losing repeated
monthly values, observations or identity errors.
Hypothesis
`test_monthly_wages_keep_equal_value_events_in_the_pre_fra_fold` independently
folds every pre-FRA monthly wage, including mixed equal-value encodings.
`test_external_parameter_collections_preserve_sources_and_table_order`
checks source multiplicity and positional parameter tables.

## Shared result and denominator contract

G's round-12 integration changes provenance checks, with no change to
Act 203's deduction amounts or coverage. `RETConfigurationUnsupported`
remains a `FamilyConfigurationUnsupported` with code
`FAMILY_CONFIG_UNSUPPORTED`, and accepts exactly `RETUnsupportedReason`;
the original R2 `UnsupportedReason` import remains an alias. Each Track B
layer has its own declared refusal and reason enum. `evaluate_ret` catches
the shared refusal family, validates metadata before computation, and
accepts only an unaltered `RETLedger` computed by R2 as a supported result.

The package-private `_provenance.py` capability seals grace decisions, partial allocations,
monthly and worker results, ledgers, outcomes and the shared denominator.
Direct construction, `dataclasses.replace`, `copy` and `deepcopy` raise
`InvalidFamilyInput`. Every pickle protocol and copyreg reduction path also
raises `InvalidFamilyInput`; persistence stores declared inputs and reruns
the computation. Serialized bytes cannot restore trusted derived state. Each
monthly result reconciles gross, net and deductions and floors its checks
under Act 215(g). Worker results reconcile calculated excess, charged and
uncharged amounts. The ledger verifies every beneficiary's twelve months,
crediting-month sets, provisional reconciliation and aggregate deductions,
including the separate CFR 404.440 residual. Nested alteration is rejected
before a result is consumed or counted. Allocation mapping reads check the
seal too, so a caller cannot feed an altered allocation back as partial-payment
rates or original shares. Ordinary exact built-in dictionaries remain accepted.

`GraceYearDecision` is also money evidence: its eligibility can prevent a
RET deduction. It is built only by `grace_year`, copies and validates its
nested `next_state`, and reconciles the initial/after-break categories with
current-year LMETY and protected post-1977 NSMs. `GraceYearState` remains a
constructible declaration of initial history. Beneficiary construction,
record-year construction and `apply_ret_year` each reject caller-built or
altered actual or estimated grace decisions before any coverage refusal.
`tests/test_track_b_ret_grace_provenance.py` exercises this invariant through
`test_grace_decision_rejects_public_construction_and_copy`,
`test_every_ret_admission_rejects_invalid_grace_evidence`,
`test_grace_private_capability_revalidates_nested_state_and_identities`, and
Hypothesis `test_grace_pickle_rejection_and_recomputation_preserve_money`.
Malformed-decision tests invoke the private computation capability to
exercise seal-time fields directly, retaining every invalid-field assertion.
They do not restore or serialize results.

`RETDenominator` aliases G's `FamilyDenominator`, and `count_ret_outcomes`
delegates to `count_family_outcomes`; both accept every declared layer's
sealed outcomes. Refused rows retain their rows and weights. RET money
aggregation accepts only R2 outcomes and ledgers; G's household, guard and
report consumers continue to require G results.

The additional contract invariants and executable checks are:

- Computation provenance and exact layer membership:
  `test_ret_computed_values_reject_public_construction_and_copy`,
  `test_evaluate_ret_rejects_caller_built_or_altered_ledger`,
  `test_ret_evaluator_rejects_other_layer_results_as_input_error`, and the
  Hypothesis `test_ret_evaluator_rejects_every_altered_month`, and the shared
  contract test
  `test_partial_payment_money_inputs_reject_unsealed_or_altered_allocations`
  and Hypothesis
  `test_partial_payments_reject_altered_allocation_money_inputs`.
- Input errors precede a callback or denominator contribution:
  `test_ret_evaluator_validates_metadata_before_computation` and
  `test_ret_counter_rejects_unsealed_or_altered_outcomes`.
- Counts are identical through the R2 and common counter, with refusals
  retained: `test_ret_counter_and_common_counter_have_identical_counts`
  and Hypothesis
  `test_ret_seals_pickle_and_common_denominator_preserve_rows`.
- Serialization rejects all computed results, refusals, rows and denominators
  for every pickle protocol. Private seal construction still rejects altered
  accounting fields: `test_ret_computed_values_cannot_be_pickled`,
  `test_ret_private_capability_rechecks_accounting_identities`, and Hypothesis
  `test_ret_private_capability_preserves_month_and_worker_accounting`.

## Declared inputs and detached access

Every public computation validates its declared input tree once and builds
an owned snapshot before any coverage decision. This includes
`RecordYear`, every `RETBeneficiary`, `WorkEarnings`, grace state, month and
termination declarations, and nested R1 parameters. A declaration subclass
is an input error. Numeric subclasses cannot contribute custom arithmetic:
the shared exact-number boundary accepts built-in numeric encodings and
stores fresh built-in fractions, while integer calendar fields remain
built-in integers and Boolean flags retain their declared type.

A valid post-construction input change computes exactly as a freshly built
declaration. An invalid change raises `InvalidFamilyInput`, even when the
record also requires `foreign_work` or another coverage refusal. The
reviewer's negative $0.10 gross-rate case now raises before an outcome or
denominator row exists. This preserves the existing rule that invalid
inputs do not become coverage gaps, without changing Act 203 deductions.

R2 carries no hidden mutable controller. Inputs and returned carried state
are independent copies. Altered sealed nested evidence fails validation
when consumed. `RETLedger.for_beneficiary` returns fresh sealed monthly
rows, so changing an accessor result leaves ledger history unchanged.
The tests in `test_track_b_r3_fix_round_13.py` execute every declared-field
error, generated error combinations, valid planted-value equivalence,
canonical numeric rejection and accessor/state detachment. The invariants
are recursive input validation before refusal, immutable arithmetic meaning,
and independence of admitted output from later caller input changes.

Grace benefit-type collections validate every raw element before set
deduplication. A forged value equal to a legal enum cannot disappear and
become a supported declaration. The generated
`test_r2_r3_enum_collection_types_are_checked_before_equality_collapse`
checks both input orders for grace month and carried-state declarations,
alongside the same invariant in ARF and recomputation. Exact huge wages
also remain exact through countable earnings and calculated excess;
`test_huge_exact_ret_money_and_recomputation_caps_do_not_overflow` checks
that boundary without changing any statutory rate or threshold.

All beneficiary identities and partial-payment mapping keys are nonempty
built-in strings. A mutable object used as a mapping key could previously
change its hash after admission, break a lookup and leave the seal matching.
The public apportionment function, private seal validation and lookup
accessors now reject such keys, including string-enum subclasses. The
same rule covers beneficiary, number-holder, monthly-result and worker
identities. `test_ret_partial_mapping_keys_are_builtin_nonempty_text`
executes the property at computation, sealing and lookup;
`test_ret_identity_slots_reject_string_enum_subclasses` covers each
identity slot. This changes no apportionment for declared valid inputs.

The binding-survivor fixture states its care facts explicitly. Both
`child_in_care=False` and `child_in_care="cdb"` produce a $796.40 widow
rate and $0 CDB auxiliary rate, retaining the entitled CDB's $750 original
share. Part (b) now computes widow excess $100: January final payable
$696.40/check $696 and provisional payable $0. The CDB remains at $0,
because GN 02603.050A.2 excludes a zero dual-entitlement rate regardless
of other deductions. No work deduction or ARF credit is attributed to the
CDB. `test_binding_survivor_maximum_with_zero_rate_cdb_computes_part_b`
executes both care assertions. The former claim that the CDB necessarily
regains room was too broad; technical entitlement still matters to the
separate NH partial-allocation rule. G still requires the child's identity
for positive care, and RS 00615.340's mother/father comparison does not
increase this widow's rate.

## Authority and inputs

The authorities are [Act 203(b), (f), (h)](https://www.ssa.gov/OP_Home/ssact/title02/0203.htm),
[20 CFR part 404 subpart E](https://www.ecfr.gov/api/versioner/v1/full/2026-10-07/title-20.xml?part=404&subpart=E),
and the POMS sections identified below. Those section citations refer to
the manifest's captured bytes; no source was fetched during this build.
The eCFR capture is the version as of 2026-10-07. The SSA publication and
benefit-planner examples are their captured 2026 versions.

`WorkEarnings` contains twelve exact, nonnegative wage amounts in the
months earned, signed annual net earnings from self-employment (NESE),
the months of self-employment, and substantial-service months. The caller
has already determined countable earnings under RS 02505.005 and whether
services are substantial under RS 02505.065; this ledger does not derive
those classifications from an income threshold. Wages are counted when
earned, and annual NESE is counted in its reportable tax year (20 CFR
404.428(d), .429; RS 02501.080).

`RETBeneficiary` supplies an identity, twelve elected benefit types,
entitlement months, and each month's gross and original rates. G supplies
the gross dime rate after the maximum, age and dual-entitlement
reductions (RS 02501.095B.5.a), and the original benefit before those
reductions for partial-payment shares (RS 02501.110A.2). Rates may change
between months. A December COLA or a child's departure is an input rate
change; R2 does not recalculate the gross family.

Each beneficiary also supplies actual earnings, optional estimated
earnings, the RIB FRA month, the actual grace-helper decision and an
optional `estimated_grace` decision for the current-year forecast,
death and divorced-spouse facts, and flags for established statutory
own-work protections or entitlement on two records. The optional
`two_record_entitlement` declaration defaults to `None`: supplied G
monthly own-benefit facts establish two-record entitlement, while an
explicit boolean must agree with the contextual facts for that person
over the year. With no supplied G context, `None` retains the absence of
a declared second entitlement. An own benefit present in any supplied
month establishes the annual exposure; a later cessation does not erase
it. Own actual or estimated excess remains refused because RS
02501.145-.150 require charging across both records. For ledger inputs,
`fra_month=None` means FRA after the year, `0` means FRA before the year,
and `1` through `12` identifies the attainment month. Survivors use the
RIB FRA, even when their survivor-benefit FRA is earlier (RS
02501.021B.3; Publication 05-10069).

`RecordYear` identifies the number holder (NH), a living retirement or
disability record or a deceased record, all entitled and legally
deemed-entitled beneficiaries, and months with a binding maximum or
another deduction event. A living NH must be present and receive RIB or
DIB in entitled months. A deceased NH must be absent. Deemed entitlement
asserts the married-person facts of Act 203(b)(1) and 20 CFR 404.420;
the broader unmarried-child reading of RS 02501.140 is refused. An
ordinary deemed child's age-18 months must be explicit. Their Act/CFR
coverage difference is refused even with those facts established.
Deemed entitlement requires a different NH with RIB entitlement in each
applicable month. `own_work_exempt_months` accepts only CHILD or WIDOW
payment months and asserts respectively attainment of age 18 or initial
widow(er) entitlement before 60 (Act 203(f)(1)(C)-(D)); it cannot
arbitrarily protect a RIB or spouse payment.

Input errors raise `InvalidFamilyInput` before a coverage refusal. These
include floats, invalid months, negative or non-dime rates, nonzero gross
outside entitlement, duplicate identities, inconsistent death or divorce
facts, noniterable monthly inputs, infinite monetary values, invalid
own-exemption or deemed-entitlement facts, grace evidence for another
year, and a carried LMETY without its required earlier section 202
entitlement history. Missing supported R1 parameter years raise
`KeyError` before coverage refusal; a missing parameter is never silently replaced by the
prior year's amount or relabelled as a statutory coverage refusal.

## What it computes, in statutory order

1. **Annual and monthly limits.** Every annual exempt amount and rate is
   loaded through R1's `RETParameters.for_year`; the ledger contains no
   hard-coded annual limit. Under FRA all year it uses the lower amount
   and exact 1/2 rate. In the FRA-attainment year it uses the full higher
   annual amount and exact 1/3 rate against pre-FRA-month earnings. From
   the FRA month there is no own earnings test (Act 203(f)(3); 20 CFR
   404.430, .434(c); RS 02501.021B.1, B.4, B.6 and .080). The full annual
   amount applies in the year of death, including death before FRA in
   the attainment year (20 CFR 404.428(c); RS 02501.025B.3). Monthly
   limits are exact annual/12, including the fractional higher amounts
   expressly set by Act 203(f)(8)(D)(v)-(vi) for 2000 and 2001. The
   rounded charts are an explicitly nonstatutory operational sensitivity;
   they never supply the default statutory result.
2. **Countable earnings.** All months' wages and annual NESE count under
   FRA, including pre-entitlement earnings. In an FRA year, wages in or
   after the attainment month are excluded. NESE is divided across the
   self-employment months, floored to whole monthly dollars, then
   multiplied by the number of those months before FRA. `FLOOR` follows
   the literal “round down” instruction, including for losses; it is not
   labelled conservative because floor can pay more when NESE is negative.
   An explicit `DROP_CENTS` alternative truncates signed monthly NESE toward zero;
   it differs from mathematical floor only for losses (RS
   02501.080B.2.b-e; 20 CFR 404.428-.430).
3. **Excess.** `calculated_excess` returns
   `floor(max(0, countable - annual_exempt) * statutory_rate)`. The
   whole-dollar excess is computed after exact Fraction arithmetic
   (RS 02501.080B.1.d and B.2.a; Act 203(f)(3); 20 CFR 404.430(b)). The
   scalar helper reproduces the published 1999 formula example, while
   the payment ledger refuses years before 2000.
4. **NH charging.** Charge the NH's excess first, chronologically from
   the first entitled, unprotected month until recovered or the year's
   chargeable benefits are exhausted. The pool includes every payable
   benefit on the record and legally deemed-entitled benefits. A
   qualifying divorced spouse is excluded from both withholding and
   the pool when divorce has lasted at least two years, or the NH was
   entitled to RIB before the divorce (Act 203(b)(1)-(2); 20 CFR
   404.415(b), .420, .434; RS 02501.021B.5.b, .095B.2 and .140).
5. **Other workers' charging.** After NH charging, charge each auxiliary
   or survivor's excess against that person's remaining benefit only.
   Do not charge an already exhausted month again. When this frees
   binding family-maximum room for another beneficiary, readjust through
   G using that month's declared `RETFamilyMonth` statutory and household
   facts. Without those facts, retain the named refusal
   `deduction_readjustment_requires_family_context` (20 CFR
   404.434(b)(2)-(3); RS 02501.095B.3-4, .155A.3-4;
   GN 02603.020-.050).
6. **Protected months.** A worker's own excess cannot be charged in an
   unentitled month, a protected grace-year NSM, the FRA month or later,
   a DIB/DWB/CDB payment month, or an explicitly established own-work
   exemption under Act 203(f)(1)(C)-(D) (20 CFR 404.435; RS
   02501.095B.5.b and .021B.5.a). A person's own protection does not
   protect that person's benefit from another worker's excess: for
   example, the NH can charge a spouse at FRA or a married,
   deemed-entitled CDB recipient. If the NH's own excess is protected
   for a month, it cannot be charged to the family in that month (Act
   203(f)(1); RS 02501.140).
7. **Provisional suspensions.** Independently repeat the charging order
   using estimated earnings, or actual earnings when no separate
   estimate was supplied. Use `estimated_grace` for provisional grace
   eligibility when supplied, otherwise the actual grace decision.
   Withhold the entire last charged month even
   when only part of its rate is needed. The ledger records this
   withholding separately from final deductions (20 CFR 404.434;
   RS 02501.100B.2, .105; RS 02510.005 versus .015).
8. **Final partial payments.** With actual closed-year earnings, the
   last charged month can have a partial payment. For NH excess,
   apportion that partial pool by original benefit amounts, before the
   maximum, age reduction and dual-entitlement offset. Cap each share
   at its current pre-deduction rate and redistribute the excess by
   the remaining original shares. Do not round between iterations.
   An entitled beneficiary with a zero payable rate retains a positive
   original share and counts among the beneficiaries in that computation;
   post-reduction zero is not loss of entitlement.
   Two beneficiaries receive the capped rate and remaining balance as
   prescribed. With three or more beneficiaries, an overflow below $1
   ends reapportionment: retain that iteration's uncapped shares, cap
   the beneficiaries whose shares exceeded their rates, and record the
   unpaid overflow as `undistributed_subdollar_residual` (20 CFR
   404.439-.441; RS 02501.110A-B). `partial_payments` returns a
   mapping-compatible `PartialPaymentAllocation` of exact net amounts
   with an `undistributed_subdollar_residual` attribute.
   Completing redistribution after this mandatory stop is unavailable.
9. **Checks, reconciliation and crediting.** For every beneficiary-month,
   `gross = net_due + deduction`, and the 215(g) check is `floor(net_due)`.
   Check-rounding loss is not another work deduction. Reconciliation
   is the sum of final checks less provisional checks; it can be
   negative when the estimate was too low. Crediting months identify
   actual full or partial work deductions (RS 02501.021C; RS
   02501.120B.3). The residual field never creates a standalone crediting
   event; crediting follows each beneficiary-month's positive actual
   deduction. This is an R3 input; R2 does not calculate an ARF or a
   benefit increase.

For each worker, final deductions attributable to that worker equal
`charged + undistributed_subdollar_residual`. Charged excess is capped by
chargeable benefits; `charged + uncharged = excess`. The residual remains
separate from both charged and uncharged excess and is attributed to the
worker whose partial family allocation produced it. Each stopped partial
allocation has a residual strictly below $1. This does not change the
beneficiary-month identity or the final check floor.

Uncharged excess is disclosed in the worker result and expires at the
year boundary. It is not an input to another record-year. Requested
prorated or deferred work suspensions are a different administrative
path and are refused here (RS 02501.100B.1, B.4-5, .120-.125).

## Monthly limits prescribed by the Act

Act 203(f)(8)(D) opens: “Notwithstanding any other provision of this
subsection, the exempt amount which is applicable to an individual who
has attained retirement age (as defined in section 216(l)) before the
close of the taxable year involved shall be”. Its two historical clauses
expressly set:

- Clause (v): “for each month of any taxable year ending after 1999 and
  before 2001, $1,416.66 2/3”.
- Clause (vi): “for each month of any taxable year ending after 2000 and
  before 2002, $2,083.33 1/3”.

These are exact $17,000/12 and $25,000/12, respectively. RS
02501.025B.2 agrees: “The monthly exempt amount is equal to 1/12 of the
applicable annual exempt amount.” 20 CFR 404.430(a)(1) likewise says:
“The monthly exempt amount, (which is 1/12 of the annual exempt amount),
applies only in a beneficiary's grace year or years.” The statute
controls; `MonthlyLimitPolicy.EXACT_TWELFTH` is the default for every
supported year, with exact Fraction arithmetic and no monthly rounding.

The CFR 404.430(a)(2)(iii) and RS 02501.025D charts display the higher
annual/monthly pairs `$17,000 $1,417` and `25,000 2,084`. Their rounded
amounts are retained only as
`MonthlyLimitPolicy.NONSTATUTORY_CHART_CEILING`, an explicitly selected
operational sensitivity. A result obtained with it does not establish
statutory conformance at the conflicting 2000/2001 boundary. Later
bundled annual limits are exact multiples of twelve, so the two settings
coincide there.

The reviewer's minimized invented 2001 case has FRA in March, entitlement
only in February, a $1 February rate, $22,919 January wages and $2,084
February wages. Countable earnings $25,003 produce
`floor(($25,003 − $25,000)/3) = $1` excess. February wages exceed the
Act's exact monthly limit, so February payment is $0, deduction is $1
and uncharged excess is $0. The chart sensitivity protects February and
pays $1, leaving the $1 excess uncharged. The earlier invented June FRA
case at a $600 rate and $28,000 January/$2,084 February wages similarly
differs by a $600 February check. Both computations are explicitly
labelled; only the exact limit is the statutory default. Source tests
pin both fractional Act amounts verbatim against the reused Act capture.

## Mandatory sub-dollar reapportionment stop

20 CFR 404.440 says: “If the excess amount involved at any point totals
less than $1, it is not reapportioned; instead, each beneficiary is paid
on the basis of the last calculation.” RS 02501.110B.2 says: “Do not
reapportion the excess amount if at any point it totals less than $1; the
monthly benefit amount includes this last calculation.” Its instruction
“Do not round any share until the final apportionment or reapportionment
is completed” keeps all shares exact up to that stop.

The stop is the only statutory computation. A capped beneficiary keeps
its pre-deduction rate, and each uncapped beneficiary keeps its share
from the last calculation. Their exact nets plus the undistributed
residual equal the available partial pool. The residual is unpaid before
the distinct Act 215(g) check floor. It is disclosed in the allocation
and worker ledger, with attribution to the charging worker. It is not
additional excess earnings charged. Crediting follows actual full or
partial work deductions; the residual field never creates a standalone
crediting event. The former `subdollar_partial_reapportionment` refusal is retired:
the rule now computes the source-prescribed stopped allocation. There is
no complete-reapportionment policy in the statutory interface.

| Invented partial pool; caps $10/$1.90/$10; original shares 2:1:1 | Exact stopped shares | Undistributed residual | Checks |
| --- | --- | --- | --- |
| $8 | $4/$1.90/$2 | $0.10 | $4/$1/$2 |
| $9.90 | $4.95/$1.90/$2.475 | $0.575 | $4/$1/$2 |

The $9.90 case catches the settled-dollar error from continuing to
redistribute: doing so would incorrectly raise the first check to $5.
The reviewer's G-generated case likewise has rates $3.50/$0.10/$1,
originals $5/$2.50/$2.50, $3 NH excess and a $1.60 January partial pool.
It stops at $0.80/$0.10/$0.40, records $0.30 residual and pays checks
$0/$0/$0. Continued redistribution would incorrectly pay the NH $1.
The source-prescribed two-beneficiary rule is separate: a $6 pool with
caps $10/$1.90 and shares 2:1 pays exact $4.10/$1.90 without stopping
on the sub-dollar balance (20 CFR 404.440; RS 02501.110B.1).

RS 02501.110B.2 also covers a first apportionment exceeding the rates
for several beneficiaries simultaneously. All shares above their caps
contribute to that iteration's overflow before testing the $1 stop. The
invented $8 pool has caps NH $8, spouse $0 and child `599/300` dollars,
with original shares 2:1:1. Its initial shares are $4/$2/$2. The spouse
releases $2 and the child
releases `1/300` dollars, so the combined `601/300` dollars must be
reapportioned to the NH. Exact net shares are NH `1801/300` dollars,
spouse $0 and child `599/300` dollars, total $8, with no residual; the
checks are $6/$0/$1.
The deterministic regression is
`test_simultaneous_initial_caps_reapportion_combined_overflow`.

The stop-boundary property keeps both initial-cap and later-cap cases.
For a pool of `8 * scale`, spouse cap zero and child cap
`pool / 3 - overflow_cents / 100`, the child caps later only when its cap
is at least the initial `pool / 4` share. At `scale=1`, 66 cents preserves
that condition, while 67 and 68 cents cap both auxiliaries initially.
The property's exact monetary, residual and conservation assertions
follow the applicable iteration rather than assuming that only the
spouse caps first (RS 02501.110B.2).

RS 02501.110 Example 3 still reproduces exact $38.50/$16/$19.25/$19.25
and checks $38/$16/$19/$19: the spouse cap releases $2.60, so the next
reapportionment is required. The 20 CFR 404.440 worked example still
gives checks $75/$16/$16/$16, with the displayed-rate and printed-pool
discrepancy pinned side by side below. These examples exercise
reapportionment without a sub-dollar stop; the invented pools and
G-generated case execute the threshold itself.

## The pure grace-year state

`grace_year` takes twelve `GraceMonth` inputs, a carried `GraceYearState`,
the FRA month and explicit termination events. Entitlement and the elected
payment type are separate. The caller carries the returned `next_state`
through consecutive calendar years; an omitted year is an input error.
The helper uses no population data and performs no monetary calculation.

The initial grace year is the first year from 1978 with an eligible NSM
during entitlement and before FRA. Act 203(f)(1)(E) expressly starts
with the “first month after December 1977”; earlier months preserve
entitlement history without consuming initial grace. A different section
202 legal type after at least one month without section 202 entitlement
can create another grace year when its first eligible NSM occurs.
Pending eligibility survives a year with no NSM (20 CFR 404.435(b)(1)-(3);
RS 02501.030B.1-2).
Changing spouse to divorced-spouse does not create a new legal benefit
type: both are Act 202(b)/(c) benefits (RS 02501.030B.1-2 and D).
For the same comparison, `CDB` and `CHILD` are child's benefits under
Act 202(d), and `DWB` and `WIDOW` are widow(er)'s benefits under Act
202(e)/(f). A change between these classifications after a gap cannot
create new after-break eligibility or overwrite LMETY. This normalization
compares every entitled section 202 benefit, including months entered as
`DWB` or `CDB`. Entry to a genuinely different normalized legal type
after a gap establishes pending eligibility even when that first month
is a disability month. `DIB` is a distinct section 223 benefit. A
DIB-only month neither replaces the last section 202 legal type nor
ends its section 202 break, and cannot itself establish different-type
eligibility. Thus a SPOUSE/DIB/WIDOW sequence can create after-break
grace, while SPOUSE/DIB/SPOUSE cannot; a separate entirely unentitled
month is unnecessary. Concurrent DIB does not interrupt continuing
section 202 entitlement (Act 203(f)(1)(E)). The carried state keeps
`previous_entitled_types` and `gap_since_entitlement` for the complete
history, while `previous_section_202_types` and `gap_since_section_202`
retain the separate statutory type comparison through DIB-only months.
A directly constructed state with an LMETY must supply or imply its
previous section 202 type. An LMETY plus latest DIB-only entitlement
without that earlier section 202 information is incomplete input and
raises `InvalidFamilyInput`; assuming a type would change grace money.
A DIB-first history with no LMETY remains valid without a section 202
history. Carrying the returned state preserves all required facts.
This comparison does not change the disability-month exclusion: the
first eligible NSM establishes the new grace year and updates LMETY
(20 CFR 404.435(b)(2)-(3); RS 02501.030B.2 and C).

Child, young-spouse and mother/father terminations can supply a termination
grace year. Child's benefits under Act 202(d) include both ordinary
`CHILD` and disability-based `CDB` (Act 203(f)(1)(F); 20 CFR
404.435(b)(4); RS 02501.030B.3.a). Ending CDB entitlement in a mixed
ordinary-child/CDB year can therefore protect the earlier ordinary-child
NSMs. The CDB months remain ineligible NSMs under 404.435(b)(3), and
a year entitled solely to DIB/DWB/CDB cannot have a grace year even
when CDB entitlement ends normally (RS 02501.030B.4).
It belongs to the year of the last entitled month: a January
termination belongs to the preceding December's year. Death, contiguous
conversion, conversion to an aged spouse and mere child-in-care failure
do not qualify. A termination-only grace does not overwrite LMETY. Any
Social Security entitlement, including DIB, in the next month excludes
the termination grace when that next month is present in the current
year's inputs, even if a caller labels the ending event normal. For a December ending,
the caller must establish a January conversion exclusion through the
termination reason; this year's helper cannot infer next year's elected
benefit (20 CFR 404.435(b)(4); RS 02501.030B.3 and D).

`met_eligible_months` records months in which the monthly test can apply
under the selected disability reading; `protected_months` records the
actual NSMs used to establish the year's status. The ledger applies the
monthly wage and substantial-service facts separately to actual and
estimated earnings over the eligible months. It does not assume that
the same months are NSMs under two different earnings reports (RS
02501.030C; RS 02510.005, .015).

DIB/DWB/CDB-only years cannot create NSMs or apply grace. A genuinely
different section 202 type entered as DWB or CDB after a gap can still
carry pending eligibility to a later year's first eligible NSM; the
disability-only-year exclusion does not erase that entitlement history
(20 CFR 404.435(b)(2)-(3); RS 02501.030B.2 and B.4).
The conservative default also
excludes simultaneous disability entitlement, following 20 CFR
404.435(b)(3). The named POMS alternative permits NSMs in months RIB is
elected while technical DIB entitlement continues, reproducing RS
02501.030B.4's published example. The money-changing difference is
recorded under Needs Max's judgment.

## Supported and refused configurations

The default R1 bundle supplies published annual values through 2026.
Later years need R1 parameters from an explicitly permitted input vintage;
the ledger does not project or fill missing years. The nonmonetary grace
helper processes pre-1978 entitlement history so the state at a supported
payment year is explicit, but only qualifying months from January 1978
can consume initial grace. This is a current-law history calculation,
not a reconstruction of monetary RET under pre-1978 law.

| Configuration | Result or refusal reason | Authority and boundary |
| --- | --- | --- |
| Calendar record-year from 2000 with an available R1 year | Supported | Act 203(f); RS 02501.021B.6 |
| Living RIB worker and spouse/divorced-spouse/child beneficiaries | Supported with the supplied G rates | RS 02501.095 |
| Disability NH, or DIB/DWB/CDB elected payment months | Supported own-work exemption; RIB elections remain tested | RS 02501.021B.5.a |
| Deceased record and widow(er), mother/father or child own work | Supported; binding readjustment requires monthly G facts | RS 02501.095B.3, .155A.3–4 |
| Variable monthly rates and entitlement | Supported; twelve months retained | RS 02501.100B.1 |
| Pre-1978 entitlement history | Supported for carried legal types and breaks; pre-1978 NSMs never consume initial grace | Act 203(f)(1)(E)'s first qualifying month after December 1977 |
| DIB-only months between section 202 entitlements | Supported; preserve the previous section 202 type and its break, so only a genuinely different later section 202 type creates after-break eligibility | Act 203(f)(1)(E); 20 CFR 404.435(b)(2)-(3); RS 02501.030B.2 |
| Normal CDB termination in a mixed ordinary-child/CDB year | Supported termination grace for eligible ordinary-child NSMs; disability-only years, disability NSMs and other termination exclusions stay excluded | Act 203(f)(1)(F); 20 CFR 404.435(b)(3)-(4); RS 02501.030B.3-4 |
| Re-entitlement after a gap to the same legal child or widow(er) type, including CDB/CHILD and DWB/WIDOW changes | Supported without a fresh after-break grace; initial grace and pending genuinely different-type eligibility remain available | Act 202(d), (e)/(f); 20 CFR 404.435(b)(2)-(3); RS 02501.030B.1-2 |
| Genuinely different section 202 entitlement entered as DWB or CDB after a gap | Supported pending after-break eligibility until an eligible ordinary-benefit NSM; disability months remain ineligible and DIB alone does not create pending eligibility | 20 CFR 404.435(b)(2)-(3); RS 02501.030B.2, B.4 |
| Three-or-more-beneficiary partial pools with a sub-$1 capped overflow | Supported with the mandatory stop and an explicit undistributed residual | 20 CFR 404.440; RS 02501.110B.2 |
| Qualifying divorced spouse | Excluded from NH charging; own earnings still tested | Act 203(b)(2); RS 02501.021B.5.b |
| Legally married deemed-entitled CDB or mother/father recipient | Supported against NH excess when the legal facts are asserted | Act 203(b)(1); 20 CFR 404.420 |
| Two-record entitlement with no actual or estimated excess | Supported; no coordinated charging is needed | RS 02501.145-.150 |
| Payment year before 2000 | `YEAR_BEFORE_2000` / `payment_year_before_2000` | FRA-era charging rules differ; RS 02501.021B.6 |
| Fiscal taxable year | `FISCAL_YEAR` / `fiscal_taxable_year` | RS 02501.025C.2, .075 |
| Short taxable year | `SHORT_TAXABLE_YEAR` / `short_taxable_year` | RS 02501.025C.3; modern death years use the full annual exemption |
| Requested prorated suspensions | `PRORATED_SUSPENSION` / `prorated_work_suspension` | RS 02501.100B.5, .120-.125 |
| Requested deferred suspensions | `DEFERRED_SUSPENSION` / `deferred_work_suspension` | RS 02501.100B.4 |
| Protested partial current-year suspension | `PROTEST_PARTIAL_SUSPENSION` / `protested_partial_work_suspension` | RS 02501.100B.3 requires a different provisional path |
| Auxiliary/survivor own deduction with a binding maximum and complete monthly G facts | Supported full/partial permanent deductions and full estimated suspensions | Act 203(a)(4); RS 02501.155A.2–4; GN 02603.050C/D |
| Separate-household nondeductees | Final increases are paid; estimated increases wait unless in the worker's household | RS 02501.160; GN 02603.090 |
| Binding readjustment without monthly G facts | `FAMILY_CONTEXT_REQUIRED` / `deduction_readjustment_requires_family_context` | Reduced rates do not identify original age and dual-entitlement facts |
| NH reservation combined with auxiliary age reduction | G `deduction_age_work_interaction` | GN 02603.050C/D reserves both amounts; current captures do not settle the interacting reduced-rate derivation |
| Two-record entitlement with actual or estimated excess | `TWO_RECORD_EARNINGS` / `excess_earnings_on_two_records` | RS 02501.145-.150 require coordinated records |
| Noncovered foreign work | `FOREIGN_WORK` / `noncovered_foreign_work` | Act 203(c); 20 CFR 404.417-.418 |
| Refusal of vocational rehabilitation | `VOCATIONAL_REHABILITATION` / `vocational_rehabilitation_refusal` | RS 02501.130 |
| Another deduction event on the record | `OTHER_DEDUCTION` / `other_deduction_event` | Act 203(c)/(d); RS 02501.130; GN 02603.040 |
| Unmarried purported deemed entitlement | `DEEMED_ENTITLEMENT_BASIS` / `deemed_entitlement_marriage_basis` | RS 02501.140's wording is broader than Act 203(b)(1)/20 CFR 404.420 |
| Ordinary deemed adult CHILD with asserted marriage and age facts | `DEEMED_ENTITLEMENT_BASIS` / `deemed_entitlement_marriage_basis` | Act 203(b)(1)'s adult-child wording is broader than CFR .420's disabled-child basis |

The monthly G context establishes maximum membership, original age
reduction and dual entitlement. Its declared baseline must match the R2
rates, original shares and binding flag. Missing contexts are named
coverage refusals; mismatched contexts are input errors. An earlier G
coverage refusal is held until every supplied month's consistency checks
finish, so later invalid inputs cannot enter a refusal denominator.

Each coverage refusal is a `RETConfigurationUnsupported`, a subclass of
G's `FamilyConfigurationUnsupported`, and has the common
`FAMILY_CONFIG_UNSUPPORTED` code plus the R2 reason. `evaluate_ret`
catches coverage refusals only; invalid input propagates.
`count_ret_outcomes` retains every supported or refused row and weight,
including counts by reason. `weighted_ret_total` raises
`FamilyTargetBlocked` if any row was refused. A refusal cannot improve
the apparent coverage denominator by disappearing.

Every month-set constructor validates the raw elements before deduplicating:
each must have `type(month) is int` and lie in 1–12. Equal boolean or float
values therefore raise `InvalidFamilyInput` in either order, including
when a record would otherwise refuse for foreign work. This applies to
self-employment, substantial services, entitlement, divorced-spouse,
deemed-child age, own-work exemptions, binding-maximum and other-deduction
months, and external grace decisions' eligible and protected months.
Valid integer duplicates remain accepted as sets. Invalid input never
creates an outcome row or enters a coverage denominator (design §7).

## Executed invariants and differentials

The following are invariants of the admitted computation. Partial pools
conserve exact net shares plus the undistributed residual, rather than
requiring a redistribution forbidden by the sub-dollar rule. The
source-prescribed two-person balance rule is pinned separately. Exact
entitlements, undistributed residuals and whole-dollar checks are distinct
quantities.

In the table, unqualified property test names are in
`tests/test_track_b_ret_ledger_properties.py`.

| Invariant | Executing tests |
| --- | --- |
| Per beneficiary-month, `gross = net_due + deduction`; both actual and provisional deductions lie between zero and their respective gross rates; the check floors net | `test_every_month_conserves_exact_money_and_checks_are_floored`; `test_auxiliary_own_excess_uses_earliest_entitled_unprotected_months` |
| A worker's charged excess is capped by chargeable benefits; charged plus uncharged equals excess; final deductions attributable to that worker equal charged plus the undistributed residual; no charge exceeds excess | `test_exact_final_charges_are_excess_capped_by_chargeable_benefits`; `test_number_holders_excess_is_charged_before_auxiliarys_own`; `test_auxiliary_own_deductions_are_monotone_with_protected_months_fixed` |
| Earlier chargeable months are exhausted before later months | `test_earlier_chargeable_months_are_exhausted_before_later_months`; `test_auxiliary_own_excess_uses_earliest_entitled_unprotected_months` |
| Excess cannot carry between years | `test_excess_is_year_local_and_cannot_change_a_clean_later_year`; unit `test_uncharged_excess_does_not_carry_into_the_next_year` |
| NH excess is applied before another beneficiary's own excess | `test_number_holders_excess_is_charged_before_auxiliarys_own`; source `test_poms_02501_095_number_holder_then_auxiliary_example`; source `test_cfr_404_441_number_holder_then_spouse_with_grace_month` |
| A beneficiary's own excess cannot reduce anyone else's benefit in part (a) | `test_auxiliarys_own_excess_cannot_reduce_any_other_beneficiary` |
| Excluding a qualifying divorced spouse leaves everyone else's deduction unchanged and protects that spouse from NH excess | `test_excluded_divorced_spouse_leaves_every_existing_deduction_unchanged`; unit `test_qualifying_divorced_spouse_is_outside_number_holders_test` |
| Fixed-rate, fixed-protection annual deductions are nondecreasing as countable earnings increase | `test_each_annual_deduction_is_nondecreasing_in_number_holders_earnings`; `test_auxiliary_own_deductions_are_monotone_with_protected_months_fixed` |
| With the same rates and protections, deductions are nonincreasing as the applicable exemption increases | `test_each_annual_deduction_is_nonincreasing_in_exempt_amount` |
| FRA-month and later wages change neither countable earnings nor deductions; those own-work months remain uncharged | `test_fra_month_and_later_wages_change_nothing`; unit `test_fra_month_wages_and_later_wages_are_not_counted`; source `test_poms_02501_080_fra_wage_and_nese_examples` |
| Grace-year NSMs are never charged to their worker's excess | `test_grace_year_nonservice_months_are_never_charged`; unit `test_grace_nonservice_months_protect_own_benefit` |
| DIB payment months are exempt from the NH's own work, and elected RIB months are tested | `test_disability_months_are_exempt_but_elected_rib_months_are_tested` |
| DWB/CDB payment months are exempt from that recipient's own work | `test_disabled_auxiliarys_own_excess_never_reduces_disabled_benefit`; unit `test_disability_benefits_are_exempt_from_their_own_work_test` |
| With identical actual and estimated earnings, grace status and protected-month facts, provisional suspensions are full months, cover final deductions in aggregate, and have nonnegative reconciliation | `test_equal_estimate_provisional_suspensions_are_full_and_cover_final`; source `test_publication_05_10069_current_year_suspension_and_next_year_repayment` |
| Crediting months reflect actual full or partial work deductions; the residual field never creates a standalone crediting event; reconciliation equals final less provisional checks | `test_crediting_months_come_from_actual_full_or_partial_deductions`; unit `test_actual_and_estimated_earnings_are_separate_inputs`; unit `test_entitled_zero_rate_auxiliary_keeps_its_original_partial_share` |
| Results are deterministic and beneficiary-order independent | `test_determinism_and_beneficiary_order_independence` |
| Partial net shares plus the residual conserve the pool, obey each cap and preserve original-share proportions among uncapped beneficiaries; each stopped allocation has a residual in [0, $1) | `test_partial_payments_preserve_total_with_residual_and_caps_and_proportions`; `test_subdollar_stop_keeps_exact_last_uncapped_shares_and_capped_rate`; source `test_cfr_404_440_and_poms_02501_110_stop_at_subdollar_last_calculation` |
| Partial reapportionment is deterministic and input-order independent | `test_partial_reapportionment_is_deterministic_and_order_independent` |
| An overflow of exactly $1 must be reapportioned; simultaneous caps contribute their combined overflow; later iterations retain every already-capped beneficiary and use the original entitled-participant count for the three-person stopping rule | `test_stop_threshold_and_later_iteration_keep_original_participant_count`; `test_simultaneous_initial_caps_reapportion_combined_overflow`; unit `test_exactly_one_dollar_overflow_is_reapportioned`; unit `test_later_subdollar_stop_retains_previously_capped_beneficiary` |
| R1 annual amounts and exact rates match every supported bundled year, with zero tolerance | `test_r1_differential_matches_every_supported_year_exactly`; `test_r1_differential_statutory_default_is_exactly_one_twelfth` |
| The default statutory monthly limit is exactly annual/12, with zero tolerance; wages above it cannot protect a grace month | `test_r1_differential_statutory_default_is_exactly_one_twelfth`; readings `test_property_default_monthly_limit_is_exact_twelfth_and_controls_grace_wages`; unit `test_act_203_f_8_d_vi_exact_limit_is_not_chart_ceiling`; source `test_act_203_f_8_d_v_vi_monthly_amounts_are_quoted_and_equal_annual_twelfths` |
| Missing R1 years raise rather than substitute | `test_r1_differential_missing_year_raises_without_substitution`; unit `test_missing_parameter_year_is_not_carried_forward` |
| G monthly own-benefit facts establish annual two-record exposure, including own-benefit onset or cessation between supplied months, independently of month, beneficiary and household order; an omitted flag cannot admit actual or estimated excess | review `test_contextual_own_rib_requires_two_record_refusal`; property `test_two_record_derivation_is_order_independent` |
| A declared two-record flag contradicting supplied G facts is an input error and creates no outcome or denominator row | review `test_declared_two_record_contradiction_is_input_error` |
| Missing supported R1 years precede held G coverage refusals and create no outcome or denominator row | review `test_missing_r1_parameter_precedes_held_g_refusal`; property `test_unavailable_supported_r1_year_is_never_a_coverage_row` |
| R2 emits G own-work events only for positive actual deductions; a person with zero excess never becomes a deductee in either actual or estimated runs | review property `test_r2_emits_only_positive_actual_deduction_events` |
| Every outcome row and weight stays in the coverage denominator; any refusal blocks an aggregate | `test_coverage_denominators_keep_every_supported_or_refused_row`; unit `test_coverage_denominator_keeps_refusals_and_blocks_aggregate` |
| Exact 1/2 and 1/3 excess rates use an integer floor: excess is nonnegative and differs from the unrounded amount by less than $1 | readings `test_property_excess_uses_exact_statutory_rate_and_dollar_floor`; unit `test_lower_threshold_and_whole_dollar_floor`; unit `test_fra_threshold_uses_one_third_and_floors`; R1 differential above |
| Invalid input is never counted as a statutory coverage gap | `test_coverage_denominators_keep_every_supported_or_refused_row`; unit `test_invalid_wage_inputs_raise_before_coverage_refusal`; `test_invalid_rates_raise_before_coverage_refusal`; `test_duplicate_identity_is_invalid_even_in_an_unsupported_record`; `test_invalid_inputs_are_not_counted_as_coverage_gaps` |
| Every raw month-set element is validated before deduplication, independent of order; valid integer duplicates in the ledger preserve the same set | `test_every_raw_month_set_element_is_validated_before_deduplication`; `test_valid_month_set_duplicates_and_order_preserve_the_same_months`; grace `test_property_external_grace_month_sets_validate_before_deduplication`; unit `test_invalid_self_employment_month_collision_is_an_input_error`; `test_invalid_entitlement_month_collision_precedes_foreign_work_refusal` |
| Under the explicit POMS election reading, only eligible elected RIB NSMs receive grace protection; the conservative CFR reading supplies none during concurrent disability entitlement | readings `test_property_explicit_poms_election_protects_only_eligible_rib_months`; `test_simultaneous_dib_rib_source_readings_change_4200_dollars` |
| Actual and estimated grace statuses are distinct; changed service facts can require recovery even when annual earnings coincide | readings `test_estimated_initial_grace_and_actual_grace_are_separate`; `test_property_changed_grace_estimate_can_require_recovery` |
| Zero payable caps retain their original shares and count toward the three-beneficiary sub-dollar stop; exact net shares plus the residual conserve the pool | `test_zero_cap_participants_preserve_total_and_trigger_source_stop`; unit `test_entitled_zero_rate_auxiliary_keeps_its_original_partial_share` |
| Explicit Act 203(f)(1)(C)-(D) protections exempt only the recipient's own work in asserted CHILD/WIDOW months | readings `test_property_other_statutory_own_exemptions_protect_only_that_workers_excess`; `test_own_work_exempt_flag_requires_a_statutory_benefit_type` |
| The test-only broader deemed-CDB reading agrees exactly with the supported married full-family charge; the Act/CFR reading preserves the unrelated record, while the public unmarried input always refuses | readings `test_property_deemed_counterfactual_matches_full_married_charge`; `test_unmarried_deemed_entitlement_counterfactual_changes_200_dollars` |

The `ss/benefits.py` float oracle has no earnings-test ledger implementation,
so there is no second RET-payment implementation against which to invent a
float differential. The implemented shared surface is R1's parameters,
with exact comparisons and no tolerance. G's `whole_dollars` helper is
shared directly; the independently calculated example checks and property
floor assertions verify its use after net entitlement.

The grace-state invariants are executed in
`tests/test_track_b_ret_grace.py`:

| Invariant | Hypothesis test |
| --- | --- |
| Protected months are exactly eligible, entitled, non-disability, pre-FRA NSMs under the chosen reading | `test_property_only_entitled_nondisability_prefra_nonservice_months_protected` |
| Grace results are deterministic and benefit-type input order independent | `test_property_determinism_and_type_order_independence` |
| Annual carried decisions equal an independent full-history reference exactly for kinds, eligible/protected months, LMETY and pending after-break eligibility | differential `test_property_carried_grace_equals_independent_full_history` |
| Pre-1978 NSMs never consume initial grace; the first qualifying post-1977 NSM establishes the initial year while earlier entitlement history remains carried | `test_property_pre_1978_nsms_cannot_consume_initial_grace`; ledger `test_pre_1978_nsm_preserves_initial_grace_and_one_dollar_mother_check` |
| Carried complete and section 202 histories remain distinct through DIB-only months and survive dataclass reconstruction unchanged; contradictory section 202 fields or LMETY without prior section 202 history are input errors; DIB-first history with no LMETY remains valid | `test_property_dib_preserves_section_202_state_through_round_trip`; `test_inconsistent_section_202_history_is_an_input_error` |
| A DIB-only bridge has the same subsequent section 202 grace decision as an equally long section 202 gap; it preserves the previous legal type, with fresh after-break grace only for a genuinely different later type | `test_property_dib_only_bridge_equals_section_202_gap`; `test_dib_bridge_compares_last_section_202_type`; ledger `test_dib_bridge_preserves_after_break_grace_and_one_dollar_widow_check` |
| With no pending eligibility, continuous section 202 entitlement cannot create a second initial/after-break grace | `test_property_continuous_entitlement_cannot_create_second_grace` |
| A new after-break grace requires a gap and a different legal type; the same type never renews it, including both directions of CDB/CHILD, DWB/WIDOW and spouse/divorced-spouse changes | `test_property_new_type_requires_gap_but_same_type_never_renews`; `test_property_same_legal_type_gap_never_creates_new_grace`; ledger `test_carried_child_cdb_same_legal_type_gap_charges_one_dollar_january` |
| Legal-type normalization retains an unused initial grace and pending eligibility for a genuinely different type across disability months and a further same-type gap | `test_property_legal_type_normalization_preserves_initial_and_pending_grace` |
| A termination-only grace leaves LMETY unchanged; its status can exist with no eligible or protected NSM, and next-month DIB still excludes it | `test_property_termination_only_never_changes_lmety`; `test_property_next_month_dib_blocks_termination_grace`; differential `test_reference_termination_status_does_not_require_an_eligible_nsm`; `test_reference_next_month_dib_blocks_termination_but_is_section_202_gap` |
| Mixed ordinary-child/CDB termination protects exactly ordinary-child pre-FRA NSMs, excludes CDB months, preserves LMETY and gives deterministic results | `test_property_mixed_child_cdb_termination_protects_only_child_nsms`; ledger `test_mixed_child_cdb_termination_grace_preserves_one_dollar_january_check` |
| A disability-only year has no grace even when CDB entitlement ends normally | `test_property_disability_only_cdb_termination_has_no_grace` |
| CDB termination keeps every excluded cause and the next-month entitlement exclusion | `test_property_cdb_termination_keeps_cause_and_next_month_exclusions` |
| Termination-event order does not change the decision or next state | `test_property_termination_event_order_independence` |
| The POMS election reading uses RIB receipt while preserving technical disability entitlement history | `test_property_poms_rib_election_separates_entitlement_from_receipt` |
| Returned state advances exactly one year, without mutating the input state | `test_property_state_advances_exactly_one_year_without_hidden_mutation` |
| Pending after-break eligibility survives a year without an NSM | `test_property_after_break_eligibility_survives_year_without_nonservice` |
| After a gap, DWB/CDB entry creates pending eligibility exactly when its normalized section 202 type is genuinely different; a same legal type or DIB entry cannot create it; disability-only years apply no grace but retain pending eligibility for the first eligible NSM | `test_property_disability_reentry_compares_legal_types_before_nsm` |
| DWB/CDB after-break eligibility is retained until the first eligible ordinary-benefit NSM, with gap placement, disability duration, work conditions and FRA controlling when it is consumed | `test_property_disabled_different_type_preserves_pending_until_eligible_nsm`; `test_different_type_entered_as_disability_gets_same_year_after_break_grace`; ledger `test_carried_different_disability_type_grace_preserves_one_dollar_february` |
| A second gap with the same benefit type cannot erase pending post-break eligibility before the first eligible NSM | `test_property_pending_grace_survives_another_same_type_gap`; `test_same_type_gap_does_not_erase_pending_grace` |

The source invariants are executed by
`test_manifest_pins_every_capture`,
`test_every_capture_is_used_by_a_conformance_quote`,
`test_rule_text_is_quoted_from_the_captures`,
`test_worked_example_figures_are_quoted_from_the_captures`, and
`test_pdf_excerpt_matches_the_captured_pdf_text`. Every capture's byte
count and SHA-256 is recomputed. The PDF helper uses `pdftotext -layout`
when available, otherwise the manifest-pinned verbatim excerpt from
those same PDF bytes. Neither branch fetches a source.

The captured XML was inspected across 20 CFR 404.415-.441. Its formal
RET worked examples are in .435 and .439-.441, all reproduced below;
.429's grain-broker illustration concerns countable-income classification,
which the caller supplies.

An estimated-versus-actual grace counterexample is intentional. With
$600 rates for all twelve months and annual earnings $24,480 + $14,400,
the beneficiary forecasts substantial services only January-May and
an initial grace with June-December NSMs. Actual substantial services
occur throughout the year, so no actual initial grace exists. Final
deductions are $7,200, provisional withholding is $3,000 and
reconciliation is −$4,200. Thus nonnegative reconciliation requires
identical protections as well as identical annual earnings. The named
example and Hypothesis property in the invariant table execute this
case; it is not labelled a defect or silently forced to zero.

A minimized grace-state counterexample exposed a defect in an early
implementation. A previously entitled CHILD recipient with LMETY 2000
entered spouse entitlement in January 2026, had no entitlement in
February, and returned to the same spouse type for a March NSM. The
second gap incorrectly erased the pending different-type grace. The
fixed transition retains pending eligibility until the first eligible
NSM, as RS 02501.030B.2 requires. Both the regression example and a
Hypothesis property execute this transition; the property minimized it
to a RIB reentry and a February gap. This was an implementation defect,
with no competing statutory reading.

Two G-generated counterexamples exposed coverage defects in the early
ledger. With PIA $1,000 and maximum $1,500, a reduced NH receives $700,
an entitled dual spouse has original $500 but payable $0 after one
delayed credit, and a dual child receives $150 with original $500. NH
excess $849 leaves a $1 January pool. Dropping the zero-rate spouse
incorrectly bypassed the three-beneficiary sub-dollar rule; retaining
all original shares now gives the mandatory stop at exact $0.50 to the
NH, $0.25 to the child and zero to the spouse, with a $0.25 undistributed
residual. The spouse has no actual deduction and no crediting month:
the residual field never creates a standalone crediting event.
`test_entitled_zero_rate_auxiliary_keeps_its_original_partial_share`
executes that zero-cap result. This example keeps the zero cap in the
allocation; the former complete-redistribution result is unavailable.
The second G-generated survivor counterexample is now computed by part
(b). PIA $1,000/max $1,500 gives a widow $796.40 and a technically
entitled CDB recipient $0 after a $650 own disability benefit, with
originals $1,000/$750. Widow age reduction is
`ceil_dime(1000 * 60 * .285 / 84) = 203.60`; widow excess $100 leaves
$696.40. GN 02603.050A.2 says to disregard the zero dual recipient
"regardless of other deductions that may apply for any other beneficiary
on record". The CDB stays $0. The remaining maximum room is unused;
there is no unsupported revival of its auxiliary benefit. Both care
variants execute in
`test_binding_survivor_maximum_with_zero_rate_cdb_computes_part_b`.

## Monetary worked examples

Every quoted monetary figure and rule is checked verbatim against its
capture. Invented earnings distributions used to generate a source's
stated excess are identified in the fixtures; they are not represented
as additional source facts. Where a published example gives a partial
pool without a recoverable annual excess, the pure partial-payment
helper is used rather than inventing an inconsistent ledger.

| Source | Figures and reproduced result | Test in `test_track_b_ret_ledger_sources.py` |
| --- | --- | --- |
| RS 02501.080B.1.d | Age 64 in 1999; $12,121 earnings less $9,600 exempt, divided by two and floored = $1,260. Scalar formula only; the 1999 ledger is refused | `test_poms_02501_080_1999_formula_example_outside_ledger_scope` |
| RS 02501.080B.2.b | FRA 6/00; $30,000 January-May wages count; $10,000 June-December does not. ($30,000 − $17,000)/3 floors to $4,333 | `test_poms_02501_080_fra_wage_and_nese_examples` |
| RS 02501.080B.2.c | $24,000 NESE across 12 months, FRA June: $2,000 × 5 = $10,000; below $17,000, so no ET deduction | Same test |
| RS 02501.080B.2.d | $44,000 NESE April-December, FRA June: monthly $4,888 after dropping the fraction; × 2 = $9,776. No ET deduction; year/month/limit errata below | Same test and `test_poms_02501_080_nese_source_errata_are_pinned_side_by_side` |
| RS 02501.080B.2.e | FRA 7/00; $24,000 wages plus $7,000 NESE June-December / 7 = $1,000 pre-FRA NESE; total $25,000. ($25,000 − $17,000)/3 floors to $2,666 | Same FRA example test |
| RS 02501.095B.2 | NH $378, spouse and child $160 each, family $698. Excess $2,094 = three months; January-March fully withheld | `test_poms_02501_095_number_holder_family_example` |
| RS 02501.095B.4 | NH $346, spouse $173, family $519; NH excess $2,076 withholds January-April. Spouse excess $865 then withholds that spouse May-September | `test_poms_02501_095_number_holder_then_auxiliary_example` |
| RS 02501.100B.2 | Monthly $562, excess $2,880: January-May consume $2,810; provisional suspensions also withhold all June | `test_poms_02501_100_full_month_suspension_example` |
| RS 02501.110 example 1 | Monthly $562, excess $2,881: final January-May withheld, $71 June deduction and $491 June paid. Provisional January-June withheld; $491 reconciliation | `test_poms_02501_110_partial_benefit_example_1` |
| RS 02501.110 example 2 | NH $800, four auxiliaries $101 each, family $1,204; excess $6,624. June partial pool $600, NH 2/6 = $200 and each auxiliary 1/6 = $100 | `test_poms_02501_110_partial_benefit_example_2_original_shares` |
| RS 02501.110 example 3 | Partial pool $93; rates NH $117, spouse $16, children $19.90 each. Initial $37.20/$18.60 shares, spouse cap frees $2.60; NH gets $1.30 and each child $.65. Exact nets $38.50/$16/$19.25/$19.25; checks $38/$16/$19/$19 | `test_poms_02501_110_partial_benefit_example_3_capped_reapportionment` |
| Publication 05-10069, lower test | $600 monthly ($7,200 annual), $26,080 earnings, $1,600 above $24,480: $800 deduction. January-February provisionally suspended; February final check $400, repaid in 2027 | `test_publication_05_10069_current_year_suspension_and_next_year_repayment` |
| Publication 05-10069, FRA November | $68,520 January-October, $3,360 above $65,160: $1,120 deduction. At $600 monthly, January-February provisionally suspended; February final check $80, repaid in 2027 | Same test |
| Publication 05-10069 special first-year rule | Retires October 30, 2026 at 62; $45,000 before retirement, $500 monthly November/December. Both months paid as NSMs under $2,040 monthly limit. The benefit rate is unstated; test uses an invented $600 rate | `test_publication_05_10069_october_retirement_special_rule` |
| Receiving Benefits While Working, under FRA | $800 monthly, $9,600 annual, $33,400 earnings ($8,920 above $24,480), deduction $4,460; yearly benefits $5,140 | `test_receiving_benefits_while_working_examples` |
| Receiving Benefits While Working, FRA August | $72,000 annual wages, $66,000 January-July ($840 above $65,160); deduction $280. First-seven-month benefits $5,600 − $280 = $5,320; full $800 from August | Same test |
| Special Earnings Limit Rule | John Smith, age 62, retires June 30, 2026 after $37,000 wages; self-employment starts October 5 with $3,000 NESE, total $40,000. Paid July-September; substantial services make October-December chargeable and fully withheld at the invented $600 rate | `test_special_earnings_limit_john_smith_example` |
| 20 CFR 404.439 | Original benefits NH $165, spouse $82.50, total $247.50; October partial pool $200. Exact $400/3 and $200/3; checks $133/$66, total $199 | `test_cfr_404_439_original_benefit_partial_payment_example` |
| 20 CFR 404.440 | Stated maximum $150, NH excess $25, stated partial pool $125. Displayed gross rates $100/$16.60/$16.60/$16.60 total $149.80; actual dime-rate pool is $124.80. Both yield checks $75/$16/$16/$16; exact NH is $75.20 versus $75.00 | `test_cfr_404_440_dime_sum_and_printed_pool_are_pinned_side_by_side` |
| 20 CFR 404.441 | NH $176, wife $88, family $264; excesses $1,599/$265. NH has February NSM: January and March-July withheld; August partial $249 split $166/$83. Wife own deductions February $88, August $83, September $88, October $6; October check $82 | `test_cfr_404_441_number_holder_then_spouse_with_grace_month` |

Publication 05-10069's entire annual table is reproduced by
`test_publication_05_10069_annual_benefit_table`:

| Monthly benefit | Earnings $24,480 or less | Earnings $25,000 | Earnings $27,000 |
| --- | --- | --- | --- |
| $700 | $8,400 | $8,140 | $7,140 |
| $900 | $10,800 | $10,540 | $9,540 |
| $1,100 | $13,200 | $12,940 | $11,940 |

The CFR .441 source uses the historical $340 monthly limit. The test
preserves its benefits, excess amounts, charge order and partial checks
in a supported 2026 invented earnings distribution: $6,678 January, $0
February and $2,100 March-December produce the same $1,599 NH excess
under R1's 2026 limit and February as the only NH NSM. The historical
monthly limit is quoted, not substituted into a supported R1 year.

## Grace-year worked examples

These examples exercise `grace_year`; the tests quote the entire relevant
source passages, including each date and figure.

| Source and facts | Reproduced status | Test in `test_track_b_ret_grace.py` |
| --- | --- | --- |
| RS 02501.030B.1: entitlement 01/11, FRA 08/11, NSMs 06/11 and 07/11 | Initial grace 2011, June/July protected, LMETY 2011 | `test_initial_grace_2011_before_august_fra` |
| RS 02501.030B.2: mother's benefits and NSM in 2010, termination 06/10, RIB in 2011 after a break | Initial 2010; new after-break grace and LMETY 2011 | `test_mother_2010_break_then_rib_2011_has_another_grace` |
| RS 02501.030B.3: child DOB 01/20/92, age 18 in 01/10, benefits terminate 01/10 | Last entitled December 2009; termination grace 2009 | `test_january_2010_child_termination_belongs_to_2009` |
| RS 02501.030B.3: child age 16 and first NSM in 2008; termination 03/10, re-entitlement 09/10, another termination 04/11 | Initial 2008; termination graces 2010 and 2011; LMETY stays 2008 | `test_child_reentitlement_retains_2010_and_2011_termination_graces` |
| RS 02501.030B.4: concurrent RIB/DIB 06/10 at age 62, RIB elected June-December; DIB elected 01/11; RIB again 01/12 | POMS reading gives initial grace 2010 and June-December NSMs; technical entitlement preserves LMETY 2010, so no new 2012 grace | `test_simultaneous_rib_dib_elections_preserve_2010_lmety` |
| RS 02501.030C: entitlement 02/11, $40,000 earnings in 2011, June/July below the monthly limit | June/July NSMs protected | `test_retirement_2011_40000_earnings_june_july_nonservice` |
| RS 02501.030C: DIB in 2009, no work after 2008, FRA and RIB 02/11 | DIB months in 2009/2010/01/11 create no NSMs or LMETY; RIB from FRA creates none | `test_dib_2009_through_january_2011_then_fra_rib_creates_no_nsm` |
| RS 02501.030D: entitlement 2010 with annual deductions, stops work March 2011, FRA September 2011 | First initial grace and LMETY 2011; March-August NSMs protected | `test_initial_year_2011_after_full_year_work_2010` |
| RS 02501.030D: widow LMETY 2010, elects RIB in 2011 without a break | LMETY transfers unchanged; no fresh grace | `test_widow_to_rib_without_break_transfers_2010_lmety` |
| 20 CFR 404.435 example 1: Don, age 62, retires April after $15,000 January-April, part-time wages below limit after April | Initial grace, May-December paid. Year is unspecified in source; helper uses invented 2026, and monetary ledger uses 2000 so the annual excess is positive | `test_cfr_404435_don_april_retirement_initial_may_through_december`; source `test_cfr_404_435_don_initial_grace_example` |
| 20 CFR 404.435 example 2: Marion's initial mother's-benefit grace 1998; last entitlement April 2000; widow entitlement February 2001 after a gap | Termination grace 2000, LMETY stays 1998; after-break grace and LMETY 2001 when an NSM occurs | `test_cfr_404435_marion_termination_2000_widow_2001_after_gap` |

## Source findings

RS 02501.080B.2.d describes `$44,000` NESE in `2000` and FRA in June,
but its arithmetic refers to `4/99 and 5/99` and says `Since the exempt
amount is $15,500`. The correctly dated months are April/May 2000 and
the R1/CFR/POMS-chart 2000 higher annual amount is $17,000. The $9,776
countable NESE and no-deduction result reproduce under either printed
or correct limit. Both source figures remain pinned side by side;
the source was not edited to conceal the errata.

20 CFR 404.440 uses a nominal $150 maximum and says a $25 deduction
leaves $125, while its displayed dime rates total $149.80. Starting from
the printed rates leaves $124.80, which conserves ledger money. The
nominal pool gives an exact $75.20 NH partial rate; the dime pool gives
$75.00. Both produce the source's whole-dollar checks of
$75/$16/$16/$16. The test records the 20-cent difference explicitly.

RS 02501.110 example 3 supplies a $93 partial pool but no annual excess.
Constant $172.80 monthly rates would require $943.80 excess to yield
exactly $93 in June; annual excess is required to be whole dollars.
Accordingly the test reproduces the published partial-share computation
using the pure helper, without claiming a full annual ledger from facts
the source did not supply.

The CFR Marion narrative says the child's and mother's entitlements
terminated when the child turned 16. RS 02501.030B.3.b separately says:
“Failure to have an entitled “child-in-care” does not qualify the mother
or father, young wife or husband to a termination grace year since not
having a “child-in-care” causes a suspension of benefits rather than
termination.” The helper takes a legally established termination as
an input. It reproduces Marion using the source's explicit termination
fact and excludes `CHILD_IN_CARE_SUSPENSION`; it does not infer that
a child turning 16 terminates the parent's entitlement. Tests
`test_cfr_404435_marion_termination_2000_widow_2001_after_gap`,
`test_termination_excluded_causes_do_not_grant_grace`, and
`test_normal_termination_still_excludes_next_month_other_benefit` pin
the distinction.

## Review round 3: mixed child and CDB termination

The executed minimized counterexample has ordinary CHILD entitlement in
January 2026 at age 17, disability-based CDB entitlement in February at
age 18, and established non-death termination after February with no
March entitlement. LMETY is 2025. Both entitled months have a $1.00
gross rate; original rates are $1.00. Countable annual NESE is $24,482
over twelve self-employment months, with zero wages and no substantial
services. The annual limit is $24,480 and excess is exactly
`floor(($24,482 - $24,480) / 2) = $1`.

The reviewed omission deducted $1.00 in January and paid a $0 check,
with annual checks $1. Recognizing the termination of child's benefits
under Act 202(d) gives termination grace, protects January, and pays
$1.00 / a $1 check there. February remains ineligible as an NSM and
exempt from its own work deduction, also paying $1. Annual checks are
$2, charged excess is $0, uncharged excess is $1, and LMETY remains
2025. `test_mixed_child_cdb_termination_grace_preserves_one_dollar_january_check`
failed first with January check $0 versus $1 and then passed. The three
new grace properties pin the mixed-year protection, disability-only-year
exclusion, non-death/next-month exclusions and LMETY preservation.
This corrects an implementation omission; no source erratum or new
money-changing reading was found (Act 203(f)(1)(F); 20 CFR
404.435(b)(3)-(4); RS 02501.030B.3-4).

## Review round 4: legal benefit types and raw month validation

The captured RS 02501.030B.2 enumerates “retirement, wife's, husband's,
child's, widow's, widower's, mother's, father's, or parent's” benefit
types for after-break grace. CFR 404.435(b)(2) requires a “different type
of retirement or survivors benefit”; paragraph (b)(3) separately excludes
disabled widow(er)/child months from NSMs. Neither capture establishes a
separate CDB or DWB legal type for paragraph (b)(2). Normalization therefore
uses Act 202(d)'s CHILD type for CDB and 202(e)/(f)'s WIDOW type for DWB
only when comparing types. The elected and entitled classifications
remain explicit for disability protection. New verbatim source assertions
pin the enumeration, different-type requirement and disability exclusion.

The failing-first carried-history regression starts with CHILD and initial
grace in 2024. January 2025 is CHILD, February–November is CDB, and
December is unentitled after established normal CDB termination.
Termination grace protects January 2025 and preserves LMETY 2024.
January 2026 is student CHILD, February–December is CDB, with continuous
entitlement that year and no termination event. All 2026 monthly gross
and original rates are $1.00. Zero wages, $24,482 annual NESE over twelve
months and no substantial services yield $1 excess above the $24,480
annual exemption. The reviewed implementation falsely renewed grace,
paid January $1 and annual checks $12, and overwrote LMETY with 2026.
The corrected ledger deducts $1.00 in January, pays January $0 and annual
checks $11, charges all $1 excess, leaves $0 uncharged and retains LMETY
2024. CDB months still pay $1 each under their own-work exclusion.
This is an invented case, not a published worked example or a source erratum.

The second executed minimum, `WorkEarnings(nese=1,
self_employment_months=(1, 1.0))`, hid the float by deduplicating before
validation. The foreign-work case likewise accepted entitled months
`(1, True)` and incorrectly returned `noncovered_foreign_work`.
Both orders now raise `InvalidFamilyInput` before any refusal. Hypothesis
checks cover all ten month-set fields, and valid-integer duplicate/order
properties preserve the ledger's established set behavior. External grace decisions
receive the same validation ordering. Neither finding changes a statutory
reading, d1418's defaults, or part (b)'s scope.

## Review round 5: a different legal type entered during disability

20 CFR 404.435(b)(2) places the new grace year in “the taxable year in
which the first non-service month occurs after the break in entitlement.”
Paragraph (b)(3) separately says “we will not count as a non-service
month” a disability-entitlement month. It does not remove that month's
section 202 legal type from the different-type comparison. RS
02501.030B.4 excludes grace “if entitled solely to DIB, disabled
widow(er)'s (DWB), or childhood disability benefits (CDB).” A mixed
DWB/WIDOW or CDB/CHILD year does not satisfy that exclusion.

The executed invented carried-year case has young-spouse entitlement
and initial grace in 2024, spouse entitlement through November 2025,
and an unentitled December after a qualifying termination. LMETY stays
2024. Following the former spouse's death, disabled surviving-widow
entitlement begins in January 2026, with ordinary widow entitlement
continuing from February at age 60. G's survivor PIA and original benefit
of $1.40, with an 84-month reduction period, produce a $1.00 gross rate.
Zero wages, $24,482 NESE over twelve self-employment months, and no
substantial services give exactly $1 excess above the $24,480 annual
exemption. The optional Act own-work-age exemption remains empty.

Removing DWB from the type comparison lost pending eligibility and paid
February $0 and annual checks $11. Comparing January's normalized WIDOW
type with the prior SPOUSE type establishes pending after-break
eligibility. February's first eligible NSM then creates AFTER_BREAK
grace, protects February–December and updates LMETY to 2026. January
still pays $1 under the disability own-work exclusion and remains
ineligible as an NSM. Correct February payment is $1, annual checks are
$12, charged excess is $0 and uncharged excess is $1. The regressions
also cover a same-year DWB entry after a gap and the analogous different
type entered as CDB, followed by an eligible ordinary-child month, using
invented G rates for the carried monetary cases. The properties retain
the same-legal-type rule,
DIB's distinct section 223 treatment, pending eligibility through a
disability-only year and every disability NSM exclusion.

This corrects an implementation omission rather than a source erratum
or a new statutory reading (20 CFR 404.435(b)(2)-(3); RS 02501.030B.2,
B.4). Ruling d1418's defaults and the mixed-year CDB termination rule
remain unchanged.

## Review round 6: initial-year boundary and section 202 history

Act 203(f)(1)(E) limits the first qualifying NSM to the “first month
after December 1977”. The current CFR and POMS describe the initial
grace rule without repeating that historical boundary. Their wording
does not override the explicit statutory date. The helper retains
pre-1978 entitlement and breaks, but no earlier NSM can consume initial
grace. This corrects the advertised earlier-history contract without
refusing that history.

The invented reviewer history starts with MOTHER_FATHER entitlement
throughout 1977 and a January NSM, then continuous entitlement without
NSMs through 1999. In 2000, all twelve months are NSMs. At age 20 in
1977, the mother remains below FRA in 2000, with an entitled disabled
child continuously in care. Mother and CDB gross rates are $1 per month.
Zero wages, $10,082 NESE, and no substantial services create $1 excess
over the $10,080 annual exemption. Consuming initial grace in 1977
incorrectly leaves January 2000 unpaid: mother's annual checks $11,
child's $12, family $23. Correct initial grace and LMETY 2000 protect
all twelve mother months: January $1, mother $12, child $12, family $24,
and zero excess charged.
`test_pre_1978_nsm_preserves_initial_grace_and_one_dollar_mother_check`
executes the complete carried history and payment. The Hypothesis test
`test_property_pre_1978_nsms_cannot_consume_initial_grace` varies the
earlier years from 1975–1977 and the first qualifying later year from
1978–2030. These are invented rule cases, not additional SSA-published
worked examples.

The same statutory clause enumerates entitlement under “subsection (a),
(b), (c), (d), (e), (f), (g), or (h) of section 202”. DIB under section
223 lies outside that comparison. DIB-only months therefore retain the
last section 202 legal type and count toward its break; they neither
supply an NSM nor create different-type eligibility themselves.
DWB/CDB remain in section 202 as widow(er)'s/child's legal types and
remain excluded from NSMs, retaining rounds 3–5's behavior. Concurrent
technical section 202 entitlement still prevents a section 202 break.

The second invented reviewer history has SPOUSE entitlement and initial
grace in 2024, no entitlement in January 2025, and DIB-only entitlement
February–December 2025. Ordinary WIDOW entitlement begins January 2026
after disability cessation. All 2026 months are NSMs; $24,482 NESE and
zero wages create $1 excess over the $24,480 exemption. Gross rate $1
and original rate $1.40 are held fixed. DIB replacing the prior SPOUSE
history incorrectly pays January $0 and annual checks $11. Retaining
the SPOUSE history gives AFTER_BREAK grace and LMETY 2026, January $1
and annual checks $12. The minimized bridge needs only November 2025
unentitled and December DIB after SPOUSE through October. Same-type
bridges remain ineligible for a new after-break grace.
`test_dib_bridge_preserves_after_break_grace_and_one_dollar_widow_check`
executes both the full and minimized monetary histories;
`test_dib_bridge_compares_last_section_202_type` covers same/different
legal types with and without an entirely unentitled month. The property
`test_property_dib_only_bridge_equals_section_202_gap` checks that DIB
cannot change the subsequent section 202 grace decision relative to a
gap of the same length. The round-5 disability-reentry property now
compares later RIB against the preserved section 202 type rather than
assuming every DIB/RIB sequence must lack after-break grace.
An additional input audit found that a manually supplied LMETY together
with latest DIB entitlement could omit the earlier section 202 type.
The state now rejects that incomplete seed instead of silently assuming
no prior section 202 history. The round-trip Hypothesis property checks
this input error alongside valid reconstructed and DIB-first states.
This does not exclude any complete carried history or introduce a
statutory coverage refusal.

The independent test-only reference reads the entire month timeline.
It first finds the first qualifying NSM after 1977, then identifies
termination years, then pairs consecutive section 202 entitled months
to identify a gap followed by a new legal type and searches for the
first subsequent eligible NSM. It derives each year's result from
those searches, without production's carried previous-type, gap, or
pending state machine. Its type mapping names the statutory subsections
and separately normalizes CDB/CHILD, DWB/WIDOW, and spouse/divorced-spouse.

`test_property_carried_grace_equals_independent_full_history` compares
production calls carried year by year against that model over invented
1975–2030 histories with type spans, gaps, terminations, disability
months, concurrent entitlement, work conditions, and a single FRA date.
The comparison covers grace kinds, applicability, eligible and protected
months, LMETY, and pending eligibility at zero tolerance. It exercises
both the default CFR disability exclusion and the explicit POMS election
alternative. At December terminations, inputs explicitly label known
January conversions as excluded, preserving the annual interface's
existing requirement. Captured quotations are checked by
`test_reference_rules_are_verbatim_in_manifest_captures`. This
differential establishes statutory mechanics only. Its completed run
matched all 600 generated histories and three explicit histories without
numerical tolerance; all nine differential/source-reference tests passed.

The first differential exposed an error in the draft reference's
termination guard, minimized to January 1975 concurrent CHILD/CDB
entitlement, CHILD receipt, no NSM, and a normal January CDB ending;
the remaining 1975–1976 months were empty. The draft incorrectly
required an eligible NSM in the termination year. POMS RS 02501.030B.4
instead excludes a year entitled solely to disability benefits; ordinary
CHILD entitlement means the year is not disability-only even when
concurrent CDB prevents every NSM. Production's TERMINATION status
with empty eligible/protected sets was intended. The reference now
checks that entitlement condition independently, and
`test_reference_termination_status_does_not_require_an_eligible_nsm`
pins this case. No production change or exclusion from the differential
was needed for that mismatch.

The separation is specific to section 203(f)(1)(E). Termination grace
under section 203(f)(1)(F) instead requires that the beneficiary “is
not entitled to any benefits under this title for the month following”.
Thus DIB-only entitlement in the next month still excludes termination
grace (20 CFR 404.435(b)(4)). Neither review correction changes the
concurrent-disability default, the termination exclusions, refusal
codes, or any ruling d1418 choice. No new statutory judgment or source
erratum is introduced by these two corrections.

## Needs Max's judgment

**Ruling d1418 (Max, 2026-10-12): keep the current defaults for these
readings, and reopen any one when a population target needs it.** The
computed defaults below (NESE losses floored; no non-service months during
simultaneous RIB and DIB entitlement, per 20 CFR 404.435(b)(3); own-work
protections limited to the CFR's disability-based wording) stand, and the
broader POMS deemed-entitlement reading stays refused.

The review resolved the historical monthly fractions and sub-dollar
reapportionment stop directly from the captured Act and CFR text. Those
rules are implemented above and are no longer judgment items. The
remaining money-changing readings are explicit below.
The production decision comments link the retained readings to the
source-conflict register IDs `us:oasdi-ret-negative-nese-proration`,
`us:oasdi-ret-grace-simultaneous-rib-dib`,
`us:oasdi-ret-own-work-age-exemptions` and
`us:oasdi-ret-deemed-entitlement-basis`.
`test_source_conflict_ids_are_linked_at_the_decision_lines` checks every
link at its decision, including both deemed-entitlement refusals.

### Signed NESE: floor versus dropping cents

RS 02501.080B.2.c says: “prorate the net earnings (or loss) equally
over all months the beneficiary was engaged in self-employment”. Its
note says: “When cents are involved divide the amount by 12, then drop
the cents, then round down before multiplying by the months before
the beneficiary attains FRA.” For a negative monthly amount, “drop
the cents” supports truncation toward zero, while “round down” supports
mathematical floor. The two readings agree on the published positive
NESE examples.

`NESEProrationPolicy.FLOOR` follows the literal “round down” instruction;
`DROP_CENTS` is an explicit alternative. In an invented June FRA year,
annual NESE loss −$13 over twelve months becomes monthly −$2 and
five-month −$10 under floor, versus monthly −$1 and five-month −$5
under dropping cents. With pre-FRA wages equal to R1's higher exempt
amount plus $13, countable earnings are higher + $3 versus higher + $8;
excess is $1 versus $2. A $600 January rate produces checks $599 versus
$598. Floor pays $1 more in this loss case, so it is not described as
conservative. Tests `test_negative_nese_floor_and_drop_cents_readings_are_explicit`
and `test_negative_nese_reading_changes_final_deduction_by_one_dollar`
pin the one-dollar difference.

### Simultaneous RIB and DIB entitlement

20 CFR 404.435(b)(3) says: “we will not count as a non-service month,
a month that occurred while the beneficiary was entitled to disability
benefits under section 223 of the Social Security Act or as a disabled
widow, widower, or child under section 202.” RS 02501.030B.4 instead
says: “If the beneficiary becomes simultaneously entitled to RIB and
DIB benefits, the earnings test (ET) applies to any month they elect
to receive RIB.” It adds: “Count NSMs for any month the RIB applies.”

`DisabilityGraceReading.CFR_ENTITLEMENT_EXCLUSION` is the conservative
default: technical disability entitlement prevents those NSMs.
`POMS_RIB_ELECTION` follows the express operational exception and is
needed to reproduce the POMS 2010/2011/2012 election example. Both
preserve technical entitlement history; neither invents a break when
the elected payment changes. The grace properties and
`test_simultaneous_disability_cfr_default_and_poms_alternative_are_explicit`
pin both readings. In an invented 2026 ledger, $45,000 January wages
precede entitlement to both RIB and DIB in June. The beneficiary elects
RIB at $600 monthly June-December and has no wages or services in those
months. Under the conservative reading all $4,200 is deducted; under
the POMS reading all $4,200 is paid. Test
`test_simultaneous_dib_rib_source_readings_change_4200_dollars` executes
that money difference, and
`test_property_explicit_poms_election_protects_only_eligible_rib_months`
executes the related ledger property.

### Other own-work age clauses

Act 203(f)(1)(C) prohibits charging a month “in which such individual,
if a child entitled to child's insurance benefits, has attained the age
of 18”. Clause (D) prohibits charging a month “for which such individual
is entitled to widow's or widower's insurance benefits if such individual
became so entitled prior to attaining age 60”. The preceding sentence
expressly says “but subject to section 202(s)”. This lane has no full
capture of 202(s) and does not adjudicate that additional condition.

20 CFR 404.435(a)(5)-(6) instead list “Are age 18 or over and entitled
to a child's insurance benefit based on disability” and “Are entitled
to a widow's or widower's insurance benefit based on disability”. The
POMS payment-type exemption in RS 02501.021B.5.a also lists DIB/DWB/CDB.
The Act's express age clauses appear broader than those operational
disabled-benefit descriptions.

The automatic default exemptions therefore follow the explicit
disability types. The documented `own_work_exempt_months` parameter
defaults to empty and is the alternative Act-clause assertion: the
caller must establish lawful entitlement, the age facts and any 202(s)
condition before asserting it. The ledger validates CHILD/WIDOW types
but does not derive those exemptions silently from an inferred age.
Max must decide how monthly assembly will establish and select this
broader reading. In invented $200 monthly ordinary CHILD and WIDOW
cases, earnings equal R1's lower amount plus $1,200. Default own
deductions total $600; the explicitly asserted Act exemption pays the
additional $600. Both cases are executed by
`test_optional_act_age_exemptions_are_an_explicit_600_dollar_reading`,
with the general selected-exemption property in the invariant table.

### Broader POMS deemed entitlement

Act 203(b)(1)'s third sentence says a recipient of child's benefits who
has attained age 18, or mother's/father's benefits, “is married to an individual entitled to
old-age insurance benefits under section 202(a)”, and then deems the
benefit payable on that person's wages and self-employment income.
20 CFR 404.420 similarly says “a person who is married to an old-age
insurance beneficiary” with mother's/father's or disabled-child
benefits on a third person's record is deemed entitled on the spouse's
record. RS 02501.140 instead says: “deem a retirement beneficiary's
spouse or child entitled on their record if they are receiving CDB,
mother's or father's benefits, or child's benefits based on another
person's ER.” The POMS wording appears to reach an unmarried child
more broadly than the Act/CFR marriage requirement. The Act additionally
covers an entitled adult child without expressly requiring disability;
the CFR's stated child basis uses disability. This additional coverage
difference is refused for an ordinary CHILD even after the caller asserts
lawful age-18 and marriage facts, pending Max's reading.

The default requires `deemed_married_to_nh=True` to assert the legal
marriage facts; broader unmarried cases receive
`DEEMED_ENTITLEMENT_BASIS`, as do ordinary deemed adult CHILD cases.
No monetary answer is fabricated for a
refused configuration. The lawful married benchmark has NH $400,
deemed-entitled CDB $200 and NH excess $600; the NH charge includes
the recipient's full $200 January benefit even though CDB's own
earnings test is exempt. Applying the broader wording to an otherwise
identical unmarried recipient would likewise remove $200 from that
recipient; treating the unrelated record independently leaves it
untouched. `test_unmarried_deemed_entitlement_is_refused_pending_source_judgment`
and `test_married_deemed_disabled_child_is_charged_number_holders_excess`
pin the refusal and the statutory benchmark.
`test_unmarried_deemed_entitlement_counterfactual_changes_200_dollars`
now executes both alternative readings with an explicit test-only
full-January-charge helper: the broader POMS reading pays $0 instead
of $200 on the unrelated recipient's record. Annual checks are $2,200
versus $2,400 in the otherwise identical married benchmark and separate
unrelated record. It checks the public unmarried input still refuses.
`test_property_deemed_counterfactual_matches_full_married_charge` compares
the narrow helper with the supported married ledger and separate record
over invented whole-dollar rates, with zero tolerance. This helper does
not change marriage facts or enable the broader reading through the
public API; ruling d1418's defaults remain in effect.
The Act's ordinary-adult-child wording would include the same $200 in
that benchmark. The CFR disability-only boundary refuses that ordinary
child case. `test_deemed_ordinary_child_requires_explicit_adult_age_facts`
pins invalid missing-age facts and the default coverage refusal with
established age facts; the married CDB benchmark pins the supported
$200 NH deduction.

### Scope wording for another deductee

The part-(a) brief asks for refusal when an auxiliary's own excess is
charged with a binding maximum “or any other deductee on the record
that month”. It also requires reproduction of 20 CFR 404.441, whose
rule expressly covers the same-month interaction: “Where both the
insured individual and another person entitled (or deemed entitled)
on the same earnings record have excess earnings”. Act 203(b)(1)
likewise charges a beneficiary's remaining benefits after an earlier
deduction, and 20 CFR 404.434(b)(3) specifies NH charging first.

This build interprets the other-deductee refusal as other deduction
events under Act 203(c)/(d)/222(b), represented by
`other_deduction_months`, which are always refused. Simultaneous NH
and auxiliary RET deductions without a binding maximum are supported
so the explicitly required CFR .441 example can be reproduced. That
example gives the wife's August $83 NH partial share, fully consumed
by her own excess, and her October $82 check. Interpreting the brief
as excluding any simultaneous RET deductee would instead refuse the
example, not produce a different computed amount. This scope reading
needs confirmation if the intended part-(a) boundary was broader.

## Deduction before reduction and the G contract

Act 203(a)(4) requires deductions before reduction for the maximum.
RS 02501.155A.1–2 first charges each working auxiliary or survivor's own
adjusted rate. Full deductees then leave the redistribution denominator;
partial deductees reserve their payable amount. G applies GN 02603.050C/D
and retained Parisi treatment. R2 charges NH excess first, then each
auxiliary's own excess, and submits the complete monthly event mapping
once all workers have been charged. Nonworkers alone receive readjustment.
This preserves statutory ordering and beneficiary order independence.

The public monthly entry point is:

```python
family_benefits_after_deductions(
    state: RecordState,
    beneficiaries: Sequence[Beneficiary],
    *,
    payment_month: YearMonth,
    params: SSAParameters,
    deductions: Mapping[str, BenefitDeduction],
    households: Mapping[str, str],
    standalone: bool,
    worker_deductions: Mapping[str, Fraction] | None = None,
) -> FamilyBenefits
```

R2's `RecordYear.family_months` maps exact integer months to declared
`RETFamilyMonth(state, beneficiaries, params, households, standalone=True)`
values. Ordered beneficiaries accept tuple/list; household maps contain
nonempty built-in string identities. G/RET record kind, beneficiary IDs,
benefit types, original shares, rates and binding status must agree.
The nested declarations follow the shared single-validation boundary.
Computation uses G's private validated entry and privately constructs
owned `BenefitDeduction` declarations. G/RET provenance seals, canonical
enums, one refusal class per reason enum and denominator retention remain
in force. Evaluators still establish provenance, not attribution or freshness.

Final own events use `OWN_EARNINGS_TEST`, their exact post-NH partial
payable and `permanent=True`. Provisional full-month suspensions use
`permanent=False`. `worker_deductions` carries deductions imposed on
auxiliaries for NH work: these amounts reserve maximum room and are not
redistributed. RS 02501.155B.3.c limits increases to the auxiliary's own
charge. G uses the pre-deduction allocated pool in this interaction so
preexisting dime-rounding slack cannot become an extra increase.

NH charging is retained on fixed Parisi and outside-maximum beneficiaries.
The G adapter does not restore their pre-NH payables. Only subject NH
charges enter the maximum reserve, and a fixed dual payable reserves its
post-NH amount so the same charge is not counted twice. The NH property
also checks ordinary spouse $90/children $105/$105, then NH-partial
$60/$60/$60: one child's own $30 leaves it $30, the spouse $60 and the
other child $90. For an outside-maximum divorced spouse $300 and three
$100 children, NH excess $600 leaves $100 each; a child's own $30 leaves
it $70 and raises the other children to $115 while the divorced spouse
stays $100. Own work confined to the outside-maximum recipient changes
none of the children's rates. These explicit examples and generated own
excesses $1–$59 execute in the existing NH-reservation Hypothesis test.

`BeneficiaryMonth` retains its prior declared shape for every previously
supported output. The new sealed `RedistributedBeneficiaryMonth` is used
only when final/provisional gross differs or reconstructed gross is an
exact non-dime amount after NH proration. It has an explicit
`provisional_gross`: final gross equals final net plus actual deduction;
provisional gross equals provisional net plus provisional deduction.
A delayed household increase is never mislabeled as a work deduction or
an ARF credit. Final credits alone flow to R3.

### Worked cases and invariants

RS 02501.160 gives PIA $213.10, maximum $396, original benefits $159.90,
four adjusted benefits $99 and C3 excess $555. Permanent charges are
$99 in January–May and $60 in June. C3 receives $0 then $39; the other
three receive $132 then $119. C2's January–May $33 increase is immediate
when it shares C3's household; E/C1's $33 increases wait for final
adjustment. Their final reconciliation is `5 * 33 + 20 = $185` each.
The source's original $159.90 is an upward dime rounding of its stated
PIA share; the capture does not date the example or establish why it used
that rounding. G's modern `floor_dime(213.10 * 3/4)` is $159.80. Both values are pinned
explicitly; equal original shares reproduce every listed payment exactly.
No altered PIA or unreported rounding override is used.

`test_rs_02501_160_permanent_full_and_partial_months` and
`test_rs_02501_160_separate_household_increases_wait_for_final_deduction`
execute those results. Source quotes and figures are checked against the
listed capture in `test_track_b_ret_ledger_sources.py` and
`test_captured_original_rounding_and_worked_payment_figures_are_explicit`.
An invented .155A.2 case charges C1/C3 $99 each in January; February
partials are $48/$98 and the other two rates $125. An invented NH-partial
case has PIA $600/max $900, NH gross $600 and three $100 auxiliaries.
NH excess $600 leaves $120/$60/$60/$60; one auxiliary's own $30 charge
leaves $30 and raises the other two to $75 each, retaining their $40 NH
deductions (`test_rs_02501_155_nh_partial_month_preserves_nh_deductions`).

The new executed invariants are:

| Invariant | Executed test |
| --- | --- |
| No own deduction means identical old result fields/types, with or without G context | `test_property_unused_g_context_preserves_original_result_fields` |
| Actual and provisional deductions reconcile separately to charged/withheld worker totals | `test_property_readjustment_conserves_deductions_and_preserves_order` |
| In generated unreduced survivor families, nondeductees do not lose rates; they never exceed OB, gain deduction credits, or raise family payable over its maximum | Same property |
| Separate-household temporary amounts retain the original $99 rate | Same property and separate-household worked case |
| Result amounts are deterministic and beneficiary order independent | Same property |
| Actual positive deductions alone supply crediting months | Same property and `test_readjusted_deductions_flow_to_r3_without_household_delay_credits` |
| Multiple workers are charged before their common monthly redistribution | `test_rs_02501_155_multiple_workers_charge_before_redistribution` |
| NH work retains its charge and cannot release room | NH-partial worked case |
| Invalid later context precedes an earlier G coverage refusal | `test_later_family_input_error_precedes_earlier_g_coverage_refusal` |

Absolute non-deductee monotonicity does not extend across GN .050A.1's
single-full-deduction exception: adding a second deductee restores the
age reserve required by GN .050C and can lower other rates. G's
`test_single_full_permanent_exception_disregards_age_reduction` pins the
minimized PIA $48/MAX $78 example, where the other children's rates fall
from $10 to $9.90 after a child's $0.10 deduction. The G note and final
report give the exact source conditions and derivation.

### Reading taken: temporary partial payment wording

This is the session's reading under Max's 2026-10-20 delegation, logged in
the source-conflict rulings as `us:oasdi-ret-temporary-partial-deduction`:
G follows RS 02501.160's explicit worked example (the specific case over
GN 02603.050D.2's general statement), and R2 keeps its full-month
provisional suspension, refusing the partial provisional path by name.

GN 02603.050D.2 says: "The worker's rate will always be $0.00 because
there are no partial deductions for temporary work deductions."
RS 02501.160 Example 2 nevertheless gives June C3 "$ 39", C2 "$119"
and says the extra "$20" is immediate while E/C1 wait until permanent.
R2 retains its existing full-month estimated suspension (GN .050D.2):
June C3 provisional $0, same-household C2 $132; final C3 $39/C2 $119.
The .160 partial illustration instead pays C3 $39/C2 $119 provisionally,
a difference of +$39/−$13 for those two people. G directly reproduces the
published partial-payable illustration. Selecting an administrative
partial-suspension path in R2 remains a named
`protested_partial_work_suspension` refusal rather than silently changing
the existing estimated ledger. Admitting provisional partial payments
into R2 would be a further reading, not taken here.

Facility of payment ended after December 1995 (GN 02603.075) and remains
outside supported R2 payment years. Two-record charging, combined maxima,
multiple auxiliary records and other deduction events remain refused.

## Part (b) differential and mutation evidence

`scripts/track_b_r2_cross_head.py --baseline-root <local origin/master tree>`
compares every declared field and result type at zero tolerance. The pinned
seed 53014 reproduces 240 previously supported R2 ledgers and their 240
same-record R3 RIB computations byte for byte. Canonical output SHA-256 is
`799fc9e23a902ac1ca0c2563579ceb094d0dbcd631a912305c40062cf21a5f55`.
Six binding conformance inputs, with own excess $1/$60/$99/$100/$555/$1,188,
all move from `deduction_before_reduction_part_b` to supported; none move
to another refusal. Both source trees are local and both subprocesses set
the staged-data roots to nonexistent paths.

Three isolated one-line R2 mutations were killed and then restored:
dropping the redistributed payable failed the .160 permanent example;
marking temporary events permanent failed separate-household timing;
dropping NH reservations failed the NH-partial example. Identical selected
tests passed after each restoration. The final lane verification artifact
records commands, counts, hashes and the back-to-back cost comparison.

## Build verification

The original build's five R2 test files passed all 540 cases. Three
existing Hypothesis tests were then strengthened to check auxiliary excess accounting,
invalid-input propagation and NH charging during a child's asserted
own-work exemption; all three passed. Birth-evidence exclusion tests
passed all 13 cases. Every mathematical ledger and grace-state invariant
above has an executed Hypothesis test.

All 33 original-build deliberate one-line implementation mutations caused
a selected test to fail. Each was reverted before another check, and both modules'
restored SHA-256 values are recorded with the exact commands, changes and
failing nodes in `track_b_r2_ret_ledger_mutations.json`. Mutated
implementations are not committed. The source captures stayed unchanged.

Review fix round 1 ran all seven `test_track_b_ret_*.py` files: 738
tests passed. The four minimized historical-limit and sub-dollar
regressions failed first against the unchanged reviewed implementation,
then all four passed after the fixes. The full source file passed 290
tests, including the verbatim Act amounts and the CFR/POMS stop rules.
The exact-$1 and later-iteration stop boundaries also have named example
tests and an executed Hypothesis property. Black and Ruff passed for all
ten Python files touched by the PR. Verification admits statutory
mechanics only; no real data or population computation was used.

All seven fix-round mutations were killed, and the same targeted nodes
passed after byte restoration. They cover the monthly default, strict $1
threshold, mandatory stop, original participant count, separation of
residual from charged excess, residual reporting and signed NESE floor.
They were applied only to isolated scratch package copies whose import
paths were checked; tracked implementation bytes stayed unchanged. The
exact changes, commands, failing nodes, restored results and source hash
are in `track_b_r2_ret_ledger_fix_round_1_mutations.json`. A separate
incremental-overflow allocation implementation matched 10,000 invented
pools at zero tolerance (seed 528), including zero caps, and independently
reproduced the exactly-$1 and later-iteration hand fixtures.

Birth-evidence checks passed all 13 cases with the artifact rebuild
excluded. The five independent tier collections found 6,955 unit,
3,909 artifact, 1,346 integration-PSID, 520 legacy-reproduction and 220
PolicyEngine-oracle tests, for a total of 12,950. The tier-policy test
passed with 12,949 other tests deselected. Both microdata directory
overrides pointed to nonexistent paths during whole-suite collection.

Review fix round 2 reproduced the false later-cap fixture with explicit
`scale=1, overflow_cents=67` before correcting its expectations. The
property now covers both cap orders and pins the 66/67/68-cent boundary;
the separate simultaneous-cap regression checks every exact share,
the zero residual, the $8 pool and checks $6/$0/$1. All seven RET test
files passed 739 tests. The complete 9,900-case fixture grid also passed
at zero tolerance. Production implementation bytes stayed unchanged.

Three isolated one-line mutations each failed both the corrected
property and the new deterministic regression: ignoring child caps,
retaining capped beneficiaries' weights in the denominator and changing
the $1 stop threshold to $3. Both tests passed after each scratch copy
was restored. Black and Ruff passed for all ten PR Python files;
birth-evidence checks passed all 13 cases with the artifact rebuild
excluded. These checks use only invented cases and captured sources.

The round-2 tier recount found 6,968 unit, 3,925 artifact, 1,346
integration-PSID, 520 legacy-reproduction and 220 PolicyEngine-oracle
tests, totaling 12,979. The tier-policy test passed with 12,978 tests
deselected. Both microdata directory overrides pointed to nonexistent
paths during every whole-suite collection and the tier-policy run.

Review fix round 3 first reproduced January check $0 instead of $1 in
the minimized mixed CHILD/CDB termination case, then passed the monetary
regression and four selected grace properties after the correction.
All five affected R2 test files passed 570 tests, including every source
hash, rule quotation and worked-example figure. Birth-evidence checks
passed all 13 cases with the artifact rebuild excluded. No assertion was
weakened and no test failure was suppressed.

The four source-conflict IDs are linked at their five decision sites.
The explicit test-only deemed-entitlement counterfactual executes the
$200 January difference while retaining the public refusal. Its new
property compares both readings with supported ledger computations at
zero tolerance. Three new grace properties and the expanded event-order
property execute the corrected mixed-year boundary and every retained
exclusion. The docstring and admitted scope reflect that boundary.

Six deliberate one-line CDB implementation mutations failed the intended
tests in isolated scratch packages: omitting CDB termination, allowing a
disability-only termination grace, admitting CDB NSMs, allowing excluded
causes, ignoring next-month entitlement and overwriting termination-only
LMETY. The same nodes passed after each restoration. A seventh mutation
ignored the test-only broader deemed reading; both new reading tests
failed, then passed after byte-identical restoration. Production mutation
copies were isolated and their import paths verified. Source captures
were unchanged. Black and Ruff passed on all ten PR Python files and
the four review helper scripts.

The round-3 independent tier recount found 7,120 unit, 3,929 artifact,
1,346 integration-PSID, 520 legacy-reproduction and 232 PolicyEngine-oracle
tests, totaling 13,147. The tier-policy test passed with 13,146 tests
deselected. Both microdata directory overrides pointed to nonexistent
paths during every whole-suite collection and the tier-policy run.
These checks admit statutory mechanics only; ruling d1418's defaults
remain in effect.


Review fix round 4 first reproduced the carried CHILD/CDB history's false
$1 January payment and the raw bool/float month collisions before correcting
production code. All seven RET test files then passed 797 tests, including
the source-conformance tests with five new verbatim source assertions.
All 13 birth-evidence checks passed with the artifact rebuild excluded.
Black and Ruff passed on all ten PR Python files and the scratch mutation
runner. Independent review confirmed the preserved disability exclusions,
initial and pending grace, and round-3 mixed-year termination behavior.

Five new one-line mutations were killed: omitting CDB legal normalization,
omitting DWB legal normalization, deduplicating eligible or protected grace
months before validation, and deduplicating ledger month values inside
validation. Each relevant test passed after restoration. The four grace
mutations ran in an isolated scratch package with an asserted import path;
the ledger mutation was restored before the final 797-test run. No mutation
is retained in production. Source captures and d1418 defaults stayed unchanged.


The round-4 independent tier recount found 7,380 unit, 4,046 artifact,
1,346 integration-PSID, 520 legacy-reproduction and 307 PolicyEngine-oracle
tests, totaling 13,599. The tier-policy test passed with 13,598 other tests
deselected. Both staged microdata overrides pointed to nonexistent paths
during every whole-suite collection and the selected policy-test run.
The committed-branch and working-tree diffs contain no protected files.
Changes remain uncommitted as required by this fix round.

Review fix round 5 first reproduced both carried-year DWB/WIDOW and
CDB/CHILD $1 February underpayments at the reviewed implementation.
The same-year examples and corrected disability-entry properties also
failed before the fix. All seven RET test files then passed 803 tests;
all 13 birth-evidence checks passed with the artifact rebuild excluded.
Black and Ruff passed on all ten PR Python files. All 41 source hashes
and byte counts match their manifest. No existing assertion outside the
explicitly corrected disability-reentry property was weakened.

Seven one-line mutations were killed: dropping DWB entry, dropping CDB
entry, allowing DIB to create section 202 eligibility, splitting the
DWB/WIDOW legal type, splitting the CDB/CHILD legal type, allowing DWB
NSMs and allowing CDB NSMs. Each targeted node passed after restoration
of the exact corrected implementation bytes. The full mutation details
and command evidence are in `scratch/review/fix-round-1-report.md` and
`scratch/review/r5_mutations.json`; no mutation remains in production.

The round-5 tier recount found 7,386 unit, 4,046 artifact, 1,346
integration-PSID, 520 legacy-reproduction and 307 PolicyEngine-oracle
tests, totaling 13,605. The selected tier-policy test passed with 13,604
other tests deselected. Both staged microdata overrides pointed to
nonexistent paths for every collection and the policy-test run. The
committed-branch and working-tree diffs contain no protected files.
Ruling d1418's defaults remain in effect.

Review fix round 6 first reproduced both reviewer payment defects,
including the minimized one-month DIB bridge. All 830 RET tests passed
after the corrections, including the new independent reference and
all rounds 3–5 regressions. The reference matched 600 generated and
three explicit histories; its sole newly minimized discrepancy was the
draft reference's termination guard, corrected and pinned as described
above. The five deliberate implementation mutations were killed and
production bytes restored. All 13 birth-evidence checks passed with
the artifact rebuild excluded. After tightening incomplete manually
supplied LMETY/DIB state validation, the complete RET and birth-evidence
gates passed again with no warnings. Black and Ruff passed on all twelve PR
Python files. These results admit statutory mechanics only; d1418's
defaults remain unchanged.

The round-6 independent tier recount found 7,413 unit, 4,046 artifact,
1,346 integration-PSID, 520 legacy-reproduction and 307 PolicyEngine-oracle
tests, totaling 13,632. The selected tier-policy test passed with 13,631
other tests deselected. Both staged microdata directory overrides pointed
to nonexistent paths for every whole-suite collection and the selected
policy test; that test's temporary directory was inside the workspace.

## Not in scope

No real microdata, population pipeline, behavioral response or forecast
validation is included. There is no tax-year choice procedure, fiscal
year or short-year implementation, estimate-administration interface,
foreign-work test, vocational rehabilitation adjudication or other
deduction-event computation. Claims withdrawal and changing the month
of entitlement are caller-established facts rather than a grace-year
optimization (RS 02501.070).

The ledger does not implement requested suspension prorating or
deferral, protested partial current-year withholding, two-record excess
charging, other deduction-event readjustment,
Medicare premiums, overpayment collection, ARF calculation, DRCs,
recomputation, or monthly assembly I. It reports estimated-versus-actual
check differences and actual deduction months so later milestones can
implement their own cited rules. Axiom differentials remain diagnostics
after a pinned rule exists; this build's verification remains statutory
conformance within the stated supported scope.
