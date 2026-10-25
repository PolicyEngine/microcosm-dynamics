# Track B R3: adjustment of the reduction factor and recomputation

**Verification class: statutory conformance. Build only, 2026-10-11;
statutory review fixes 2026-10-12; shared input boundary revised
2026-10-18 for PR #530 round 15.**
Admitted scope is ARF credits and earnings recomputation mechanics for
supported cases. Inputs are invented histories and captured SSA examples.
There is no population, behavioral, forecast or payment-processing claim.

The governing Track B design is revision 3, approved under ruling d515,
`microcosm-launch-evidence/dynasim-parity-20260909/trackb-design-20260928.md`.
Sections 3.1, 3.2, 5.4, 6 and 7 require separate ARF and recomputation
references, record-specific credits, preserved original computation factors,
no future earnings in earlier recomputations, and explicit unavailable
histories. Axiom comparisons remain diagnostics after a rule is pinned.

Code is `src/populace_dynamics/track_b/arf.py` and `recompute.py`. Example
and Hypothesis tests are `tests/test_track_b_arf.py`,
`tests/test_track_b_arf_properties.py`, `tests/test_track_b_recompute.py`
and `tests/test_track_b_recompute_properties.py`. Source integrity and
verbatim quotations are in `tests/test_track_b_r3_sources.py`.

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
| `RecomputationBasis.bend_points`; `exact_pia.bend_points` | Ordered fixed pair. The lower and upper thresholds have distinct positions. |
| `recompute_sequence.earnings_years` | Ordered annual history. Each step receives the preceding accepted eligibility PIA and chronology is validated. |
| `count_arf_outcomes.outcomes`; `weighted_recomputed_pia.outcomes` | Ordered observations. Preserve every row and its duplicate-key checks; distinct keys retain every count, weight and benefit contribution. |
| `ARFClaim.full_work_deduction_months`, `partial_work_deduction_months`, `child_in_care_months`, `nonentitlement_months`, `simultaneous_dib_months`, `mother_father_rate_months` | Calendar-month membership. One statutory month receives at most one credit, including when full and partial inputs overlap. |
| `ARFClaim.conditions`; `RecomputationBasis.conditions` | Membership of canonical refusal/condition enums. The presence of a flag determines coverage; repeating it does not add a refusal. |
| `ARFResult.crediting_months` (computed output) | Immutable membership of credited calendar months, not a sequence of monetary events. |
| A `(year, month)` alternative anywhere in `MonthInput` | Ordered fixed pair within the month schema. The outer credit collection has membership semantics; its month-pair elements retain their two distinct positions. |
| Earnings `history`, `december_cola_percent`, and shared SSA parameter mappings | Keyed associations with validated exact calendar-year keys. Amounts and unavailable-value markers remain attached to their years; normalization collisions are rejected. Shared SSA arrays and schedules retain the ordered classification in the G note. |

No membership field carries an amount or an event count. A `YearMonth`
and a `(year, month)` pair naming the same month normalize to one calendar
month, as required by the distinct-month credit rule in 402(q)(6)-(7),
CFR 404.412 and RS 00615.482. Repeating that month cannot increase its
credit. Every raw month still passes its own schema before set
construction, so an invalid alias cannot hide behind an equal valid value.
Repeated canonical condition flags retain the same refusal reason.

The shared tests in
`tests/test_track_b_gross_benefits_fix_round_15_collections.py` execute
`test_every_collection_schema_declares_order_or_membership`,
`test_every_collection_field_has_canonical_container_semantics`,
`test_every_public_collection_argument_preserves_its_declared_semantics`,
`test_membership_months_collapse_equivalent_month_encodings`, and
`test_membership_fields_contain_only_months_or_canonical_flags`.
Hypothesis `test_denominator_sequences_preserve_duplicate_key_errors` preserves
duplicate-key errors across the four layers instead of silently collapsing
repeated observations. Existing
`test_annual_fold_is_non_decreasing_and_matches_individual_steps` checks
the chronological recomputation fold; its monetary semantics remain
unchanged. Sets cannot represent the declared annual sequence and are now
input errors in that ordered slot.

## Statutory order

R2 supplies final full or partial work-deduction months for each benefit
record. R3 takes built-in collections of `YearMonth` or `(year, month)` values and
imports no R2 implementation. Provisional or prorated suspensions are not
final deduction months. Credits are a union, so overlapping categories
credit a month once. Only original reduction-window months count
(42 U.S.C. 402(q)(6)-(7); RS 00615.482).

Every credit-month and condition collection field in an ARF claim is
validated and snapshotted once at construction into a frozenset. Scalar
money, dates and enumeration
fields are checked immediately; cohort and entitlement-window crosschecks
using the parameter bundle still precede any coverage refusal. An ARF result freezes its crediting
months, and a recomputation basis freezes its conditions at construction;
its bend points admit a tuple or list and normalize to a tuple. Neither
evaluating the original claim nor
inspecting a result can consume credits or erase an exceptional-history
refusal. Built-in list and immutable-set inputs have exactly the same supported
results and refusal reasons. This implements deterministic record-specific
credits and retention of unsupported rows under design sections 6 and 7.

ARF input validation first rejects non-finite numeric statutory-rate,
benefit-share and bracket values, including NaN and either infinity, with
`ValueError`. It then calls G's unmodified `statutory_rates` to check the
complete shared rate bundle, including the RIB and spouse rates and their
36-month brackets (402(q)(1)(A); 20 CFR 404.410; RS 00615.101, .201).
A mismatched finite bundle retains G's original `ValueError`. Both errors
precede any explicit or automatic coverage refusal and benefit arithmetic,
and propagate through `apply_arf`, `evaluate_arf` and row construction for
`count_arf_outcomes`; no unsupported outcome or denominator is constructed
for the invalid row. Valid coverage refusals still precede benefit
arithmetic. Recomputation uses a separate parameter surface: required NAWI
and contribution bases are already checked for finite positive values
before coverage; ARF age-reduction rates and benefit shares are not inputs
to its original 90/32/15-percent formula (415(a)(1), (f)(2)(C)).

ARF applies at FRA for RIB and spouses. Ordinary widow adjustments apply at
age 62 and again at widow FRA; credits recognized at 62 persist until FRA,
without adding intervening credits early (402(q)(1)(B)(ii); 20 CFR
404.412(b); RS 00615.490, .580, .582). SSA attains age the day before a
birthday, so a first-day birth attains FRA in the previous month. January 1
also belongs to the preceding birth-year cohort (RS 00615.003, .004, .015).
Initial RIB at 62 has the separate throughout-the-month requirement.

Reduction is recalculated on the current COLA-increased unreduced amount,
already adjusted for any family maximum. G's `worker_reduction_fraction`,
`spouse_reduction_fraction`, `survivor_reduction_fraction`, `ceil_dime`,
`floor_dime` and `whole_dollars` are reused. RIB uses 5/9 of one percent for
36 months and 5/12 thereafter; spouse uses 25/36 and 5/12; widow reduction
spreads 28.5 percent across the cohort's full reduction period. The money
reduction rounds upward to a dime, then the benefit rounds downward to a
whole dollar separately (402(q)(8)-(9); RS 00615.101, .201, .301).

When own entitlement starts after completed spouse ARF, retain the single
spouse adjustment and subtract the supplied independently adjusted own
payment, bounded below by zero (402(k)(3)(A); RS 00615.500A.1). Own PIA
and payable may differ, including because of delayed retirement credits.
Varying own PIA with that payment fixed leaves this spouse component
unchanged. Reapplication retains the supplied payment. Concurrent or
preceding own entitlement uses the excess over own PIA under .500A.2.

Recomputation extends computation base years through the earnings year,
while preserving the original indexing year, computation-year count and
eligibility-year bend points (415(f)(2)(B)-(C); CFR 404.281, .284). Every
base year from 1951 through that cutoff must have an explicit nonnegative
amount, including explicit zero. A missing key or `UNAVAILABLE` raises
`InvalidFamilyInput` before any coverage refusal. Later amount values are
not read. The adapter calls `ss.statutory_aime.aime_with_computation_years`
and guards its integer floor with exact Fraction indexing and selection.
The original ordinary RIB computation-year count must be consistent with
its eligibility cohort; R3 preserves it rather than recomputing it using
the later earnings year (415(b)(2), (f)(2)(C)). Original insured status and
entitlement are supplied as established facts; earnings arithmetic does
not verify insured status or quarters of coverage. Low-level arbitrary
computation counts and synthetic parameters are formula diagnostics, not
complete claimant cases.

Required NAWI and contribution-base availability, positivity and finite
values are validated separately from AIME capping, indexing and selection.
Complete earnings and COLA histories and all required parameters are checked
before coverage. Coverage refusals precede any ordinary AIME or PIA
calculation (415(f)(2)(B)-(C); CFR 404.283-.284). An annual sequence validates
every required year through its last cutoff before its first refusal,
without calculating AIME. Unsupported formulas retain their named reason
and produce no ordinary candidate; invalid required inputs still raise
`InvalidFamilyInput` rather than being counted as coverage gaps.

PIA is the exact 90/32/15-percent formula, floored to a dime. Original bend
points are $180 and $1,085 scaled by NAWI, with half-dollar ties upward
(415(a)(1)(B); G's RS 00605.900 capture). December COLAs from the
eligibility year through the effective month are applied one by one,
flooring each increase to a dime (415(i); existing G capture). A complete
COLA history must report zero increases explicitly. The $1 rule compares
actual dime PIAs after those COLAs; whole-dollar check amounts and
eligibility-level differences cannot substitute (415(f)(4); RS 00605.501).

An ordinary recomputation takes effect in January after the earnings year.
Death-year earnings take effect in the death month when death is at or
after FRA. The alternative death-before-FRA computation in 415(f)(5) is
refused (415(f)(2)(D); CFR 404.282; RS 00605.401). December processing in
Publication 05-10069 is distinct from January statutory effectiveness.
A sequence carries only accepted eligibility-level PIAs forward. A sub-$1
candidate remains pending; later positive earnings can produce an increase
against the PIA then in force. A year with zero earnings cannot trigger
reconsideration solely because additional COLAs have accrued (RS 00605.501).

## Supported and refused configurations

All refusals carry `FAMILY_CONFIG_UNSUPPORTED` and a named reason. Invalid
inputs raise first. Both modules retain refused rows and weights through
G's denominator counter. A recomputed PIA aggregate is blocked if any
required row is refused. No refused family is replaced by a worker-only
case or removed from a denominator.

| Configuration | Treatment and authority |
| --- | --- |
| Modern single RIB, spouse or ordinary widow ARF | Supported for original entitlement from January 1978 and payment months from January 1983; 402(q)(10), RS 00615.490 |
| Full or partial final work deduction | One full credit per qualifying month, separately per record; RS 00615.482 |
| Spouse child in care and terminating-event months | Explicit certified months supported at FRA; 402(q)(7)(B)-(C) |
| RIB simultaneously entitled to DIB | Explicit months supported as credits; 402(q)(7)(F), CFR 404.412(a)(6) |
| Widow terminating-event and actual mother/father-rate months | Explicit certified months supported; 402(q)(7)(D)-(E), RS 00615.482 |
| Spouse own RIB/DIB concurrent or preceding | Reduction applied to excess over own PIA; independently adjusted own amount supplied; RS 00615.500 |
| Own benefit first entitled after completed spouse ARF | Single spouse ARF retained, independently computed own payment offset; RS 00615.500A.1 |
| Deceased RIB number holder | Hypothetical adjustment at would-have-been FRA, final RIB deductions before death month; RS 00615.598. The result is a survivor-limit component, never payment to the deceased |
| Ordinary AIME RIB recomputation | Supported eligibility from 1983, complete original basis and histories, continuous declared entitlement; 415(f)(2), CFR 404.284 |
| Death-year recomputation at or after FRA | Supported, effective death month, COLAs cut off at that month; 415(f)(2)(D)(ii) |
| Spouse reentitled before FRA | Supported: the original reduction months apply until FRA, and the ARF at FRA removes the terminated months; 402(q)(1)(B), (q)(7)(C); RS 00615.201A.1 (reading below; RS 00615.491A's earlier removal is not followed) |
| Own entitlement after spouse but before ARF | `arf_spouse_own_after_spouse_before_arf`; sequence not settled by the captured .500 procedures |
| Disabled widow and widow dual DIB or RIB | `arf_disabled_widow`, `arf_widow_dual_dib`, `arf_widow_dual_rib`; .590/.595 conversion and earlier reduction histories require additional state |
| RIB-LIM widow | `arf_widow_rib_limit`; .585 requires its separate cap and sometimes no increase despite ARF |
| Nonbinding widow child-in-care floor | `arf_widow_child_care_without_rate_increase`; refused pending Max (below) |
| Historical widow FRA | `arf_widow_fra_before_1911` or `arf_historical_widow_fra_conflict`; old FRA 62 lies outside G's survivor surface; disputed 1911 cohort below |
| Historical ARF rounding or other suspensions | `arf_initial_entitlement_before_1978`, `arf_payment_before_1983`, `arf_other_suspension`; historical reduction-ratio/rounding rules and nonwork suspensions require separate procedures |
| Historical recomputation eligibility | `recompute_eligibility_before_1983`; CFR .284's historical upward rounding differs from the shared modern helpers |
| AMW, old-start, special/frozen minimum or guarantee PIA | `recompute_non_aime_formula_pia`; CFR .283/.284(f), RS 00605.501D |
| DIB, disability freeze or prior DIB | `recompute_disability_entitlement`, `recompute_disability_freeze`, `recompute_prior_disability`; additional indexing/count, conversion and guarantee rules not implemented |
| WEP for months before 2024 | `recompute_wep_before_2024`; RS 00605.501B.2, CFR .288 |
| Administrative finality or corrections | `recompute_administrative_finality`; RS 00605.405/.580 distinguish a correct new computation from reopening/recalculation |
| Waived or disadvantageous recomputation | `recompute_waived_or_disadvantageous`; CFR .287, RS 00605.407. A higher PIA does not prove higher total family payment |
| Special earnings credits | `recompute_special_earnings_credits`; 415(f)(6) requires additional evidence |
| Death before FRA | `recompute_death_before_fra_415f5`; separate formula under 415(f)(5). Missing FRA is an input error |

## Shared result and denominator contract

R3 retains the statutory money rules above (402(q)(6)-(9) for ARF;
415(f)(2), (4) and RS 00605.501A for recomputation). Its coverage exceptions
are now declared members of the shared `FamilyConfigurationUnsupported`
family: `ARFConfigurationUnsupported` accepts exactly
`ARFUnsupportedReason`, and `RecomputationConfigurationUnsupported` accepts
exactly `RecomputationUnsupportedReason`. All carry the existing
`FAMILY_CONFIG_UNSUPPORTED` code. Each evaluator catches the shared family,
so a valid dependency refusal keeps its row and weight without changing
its original reason enum. G's 403(a)(5) guard and reason inventory continue
to accept G reasons only.

The package-private `_provenance.py` capability seals ARF results,
recomputation decisions and results, both layers' outcomes, and their
refusals. Direct construction, `dataclasses.replace`, `copy` and `deepcopy`
raise `InvalidFamilyInput`. Every pickle protocol and copyreg reduction
path also raises `InvalidFamilyInput`. Persist declared inputs and recompute;
serialized bytes cannot restore trusted derived state. `ARFOutcome.benefits` is an `ARFResult`, while
`RecomputationOutcome.result` is a `RecomputationResult`. The common
`count_family_outcomes` accepts both exact sealed outcome types and G's
outcomes, with `count_arf_outcomes` delegating to that same counter.
Unsealed or altered rows and nested values never count. Metadata is checked
before computation; input errors remain errors, outside the denominator.

Every public computation validates its declared inputs once and computes
with an owned snapshot before coverage. The shared exact-number helper
rejects numeric subclasses; no custom arithmetic object can remain in a
weight, result, parameter snapshot or denominator. Accepted exact monetary
values become fresh built-in fractions. Date/count fields retain built-in
integers. Declaration subclasses and malformed `object.__new__` inputs are
input errors. Mutating an original declaration after admission cannot alter
a computed result; a valid changed declaration is evaluated as newly
constructed, and invalid fields are rejected before any refusal.

ARF claim and spouse-own-benefit constructors validate intrinsic money,
date, month and enum fields immediately. Cohort and entitlement-window
rules still require the computation's parameters. Conditions validate
every raw element before deduplication: a string equal to a string-enum
member, or a forged object equal to a plain-enum member, cannot disappear
and turn an input error into a refusal. The generated
`test_r2_r3_enum_collection_types_are_checked_before_equality_collapse`
pins both input orders across R2 and R3; the recomputation string-enum
counterexample is also pinned separately.

Parameter finiteness checks use the shared exact-number helper without
converting arbitrary-size integers or fractions to floats. Unsupported
finite ARF rates therefore raise `InvalidFamilyInput`, including when a
coverage condition is present. Exact huge earnings retain the existing
taxable-cap behavior and exact NAWI ratios preserve bend-point arithmetic.
`test_huge_finite_arf_rate_is_an_input_error_before_coverage` and
`test_huge_exact_ret_money_and_recomputation_caps_do_not_overflow` execute
these cases.

The 1960/1959 public-pickle counterexample is blocked at `pickle.dumps`,
before bytes exist to patch. Its original 1960 claim still pays $910 with
January 2027 FRA. A freshly computed 1959 counterpart has November 2025
FRA, 46 reduction months, $985.80 and a $985 whole-dollar benefit. No
statutory amount, refusal reason or worked example changes. `test_arf_1959_1960_pickle_patch_is_blocked_at_serialization` pins
that boundary. `test_r3_mutable_fraction_weight_is_rejected_or_detached`
pins the reviewer's mutable weight attack. Generated declared-field and
numeric-subclass cases in `test_track_b_r3_fix_round_13.py` execute the
same invariants across ARF, recomputation and R2.

Each evaluator accepts only unchanged results computed by its own layer.
`apply_arf` also checks a result before using its original claim as a money
input. `weighted_recomputed_pia` requires recomputation outcomes; G's money
aggregators require G outcomes. ARF seals reconcile the original window,
distinct credits, adjusted months, effective date, factor, dime reduction,
benefit and whole dollars. Private seal construction reuses the full ARF claim-field
validator with the retained FRA, then rejects any original claim whose
known conditions, historical dates or entitlement sequence require refusal;
a fabricated supported result cannot bypass that coverage decision.
Recomputation decisions preserve `has_earnings`
as an additional diagnostic Boolean so seal construction can check the full
RS 00605.501A threshold identity: application is equivalent to positive
earnings and an increase of at least $1. Results reconcile the sealed
decision, effective year and accepted eligibility PIA. These validation
changes do not alter any supported amount or coverage reason.

`tests/test_track_b_r3_provenance.py` executes these additional invariants:

| Invariant | Executing tests |
| --- | --- |
| Results cannot be constructed, copied or replaced by callers; no sealed result can be serialized | `test_r3_results_cannot_be_constructed_directly`, `test_r3_results_cannot_be_copied_or_replaced`, `test_r3_altered_result_cannot_be_pickled`, `test_r3_sealed_result_identities_and_pickle_rejection` |
| Refusal classes bind their exact layer enum while retaining the shared catch type and code | `test_r3_declared_refusals_bind_exact_reason_enums` |
| Each evaluator validates its own result before building a row; ARF result money inputs require the same provenance | `test_r3_evaluators_only_admit_their_own_unchanged_results`, `test_r3_evaluator_rejects_before_outcome_construction`, `test_arf_money_input_rejects_unsealed_and_altered_results` |
| Invalid key or weight is rejected before invoking a computation | `test_r3_metadata_errors_precede_computation` |
| Mixed layer rows have identical counts through both counters, independent of order, with serialization rejected; refused rows and weights remain included, while altered or unsealed rows cannot count | `test_r3_shared_counter_differential_and_pickle_rejection` (Hypothesis) |
| ARF month and money identities, idempotence on recomputation, and the full recomputation threshold identity hold for generated inputs | `test_r3_sealed_result_identities_and_pickle_rejection` (Hypothesis) |
| Private seal construction cannot admit an original ARF claim that ordinary computation refuses | Private-capability tests in the shared round-12 contract file |
| Nested result calendar months are revalidated at seal construction, including months 0 and 13 | Private-capability tests in the shared round-12 contract file |
| Caller-built sibling outcomes cannot count, and sibling outcomes cannot reach G money aggregation | `test_r3_outcome_cannot_be_constructed_directly_or_used_as_g_money` |

## Executed invariants

Each row has a Hypothesis property test beside the example tests.

| Invariant | Property test |
| --- | --- |
| ARF is idempotent, deterministic and retains the original claim | `test_arf_is_idempotent_deterministic_and_preserves_original_claim` |
| Repeated evaluation of any supported or refused built-in collection ARF claim preserves results, reasons and denominator weights; result credits remain immutable on repeated inspection; immutable-set and list inputs agree exactly | `test_collection_claim_evaluation_preserves_results_and_refusals` |
| Adjusted months + distinct credits = original months; credits are bounded and only original-window months count; input order does not matter | `test_credit_bounds_window_and_order_independence` |
| More credits never lower the nominal benefit factor, dime benefit or whole-dollar benefit; the factor is nonincreasing in adjusted months | `test_more_credits_never_lower_benefit_or_nominal_factor` |
| A partial deduction counts as a full month; duplicate full/partial inputs never double credit | `test_partial_deduction_equals_full_credit_and_duplicate_categories_do_not_add` |
| RIB and spouse credits do not apply before FRA | `test_no_rib_or_spouse_adjustment_before_fra` |
| Widow age-62 credits persist; intervening credits wait for FRA | `test_widow_age62_freezes_credits_until_fra` |
| Zero credits preserve G's benefit; benefits are dime multiples in [0, unreduced amount], factors in [0, 1] | `test_zero_credits_matches_g_exactly_and_remaining_months_differential` |
| FRA follows the original cohort schedule and SSA day-before-birthday calendar | `test_fra_calendar_differential_with_original_cohort_schedule` |
| Invalid age inputs remain errors even with an exceptional-history refusal flag | `test_invalid_age_precedes_any_disabled_widow_coverage_refusal` |
| G's statutory parameter errors propagate unchanged before explicit and automatic ARF refusals through application, evaluation and counting; invalid inputs never become unsupported rows | `test_invalid_statutory_parameters_never_become_arf_refusals` |
| Non-finite numeric rates, shares and brackets raise the same input error through application, evaluation and lazy counting, before ordinary arithmetic or explicit and automatic coverage refusals; invalid rows produce neither an ARF result nor an unsupported outcome | `test_nonfinite_statutory_fields_never_create_arf_results_or_refusals` |
| After completed spouse ARF, the benefit is the nonnegative excess of G's exact adjusted spouse amount over supplied own payable; own PIA changes alone do not affect it, whole dollars floor that excess, and reapplication preserves it | `test_post_arf_own_payable_offset_is_independent_of_pia_and_idempotent` |
| Every ARF row and its weight remains in the denominator | `test_refusal_denominator_keeps_every_weight` |
| Original indexing, computation count and per-year caps match an independent Fraction reference; later NAWI cannot change earlier indexing | `test_original_index_count_and_caps_against_independent_fraction_reference` |
| Original ordinary computation-year count agrees with the statutory count and stays frozen | `test_frozen_ordinary_year_count_matches_original_statutory_count` |
| Exact PIA agrees with the float oracle within $0.000000001 on its shared formula/bend-point surface | `test_exact_pia_matches_float_oracle_to_one_nanodollar` |
| Complete integer histories agree with reused statutory AIME on the shared integer surface | `test_complete_integer_aime_matches_reused_statutory_oracle` |
| Ordinary PIA never decreases even when the candidate is lower | `test_ordinary_recomputed_pia_never_decreases` |
| A chronological annual fold equals individual steps and is nondecreasing | `test_annual_fold_is_non_decreasing_and_matches_individual_steps` |
| Later earnings, including later unavailable values, never alter earlier results | `test_later_earnings_never_change_earlier_results` |
| Earnings are capped per year before indexing and selection | `test_aime_caps_each_year_before_selection` |
| Every year from 1951 through the cutoff requires explicit availability | `test_every_statutory_base_year_requires_explicit_availability` |
| An absent or unavailable base year never becomes zero | `test_unavailable_year_never_becomes_zero` |
| PIA is nonnegative, monotone in AIME and a dime multiple | `test_pia_is_dime_multiple_monotone_and_nonnegative` |
| Application is equivalent to positive earnings and at least $1 after COLAs; rejected candidates preserve the PIA | `test_dollar_rule_exact_equivalence` |
| Earnings map order does not change results; repeated evaluation is deterministic | `test_earnings_mapping_order_independent_and_deterministic` |
| Built-in collection conditions in a recomputation basis preserve repeated supported results and refused outcomes, with every weight retained | `test_collection_conditions_preserve_repeated_results_and_outcomes` |
| Every recomputation coverage refusal precedes ordinary AIME/PIA arithmetic, in annual calls and sequences | `test_all_coverage_refusals_precede_ordinary_arithmetic` |
| Invalid required NAWI and contribution bases raise before any coverage refusal or ordinary arithmetic | `test_invalid_required_parameters_precede_refusal_without_arithmetic` |
| An invalid original ordinary computation count raises before a later death-before-FRA refusal in a sequence | `test_invalid_original_count_precedes_sequence_death_refusal` |
| Refusals retain every row and weight and block a PIA target | `test_refusals_retained_in_weighted_denominator` |
| Invalid histories are never counted as coverage gaps | `test_input_error_is_never_classified_as_coverage` |
| Death-month effectiveness excludes later COLAs | `test_death_effective_month_excludes_later_cola` |

Exact ARF comparisons against G have zero tolerance. Published-source
parameters are reused rather than fit. Deliberate rule mutations and their
failing tests are recorded in the completion report.

## Worked examples

Publication 05-10069 starts with PIA $1,300, FRA 67, claim age 62 and 60
reduction months: 30 percent reduction, $390, gives $910. Twelve crediting
months leave 48 months: 25 percent reduction, $325, gives $975. All 60
months credited give $1,300. Dime values are $910.00/$975.00/$1,300.00;
whole-dollar benefits are 910/975/1300. RS 00615.480-.598 contains no numeric
ARF worked examples, so the other ARF combinations are invented cases.

Two invented post-ARF own-entitlement cases distinguish own PIA from own
payable under RS 00615.500A.1. Both use birth January 2, 1960, first spouse
entitlement January 2022, no credits and payment January 2028: 60 RF gives
a 35-percent reduction. Unreduced spouse amount $26.20 has reduction
$9.17 rounded up to $9.20, leaving $17.00. Own PIA $15.00 with independently
adjusted own payable $15.10 leaves $1.90 and whole-dollar $1; using the
PIA as offset would instead give $2.00/$2. Unreduced $650.00 has reduction
$227.50 and adjusted spouse amount $422.50. Own PIA $200.00 and payable
$208.00 leave $214.50/$214; a PIA offset would give $222.50/$222. Both
cases and repeated application are pinned by
`test_own_entitlement_after_spouse_arf_offsets_own_payable_not_pia`. Their
figures are invented diagnostics, not published worked-example figures.

RS 00615.015 contains twelve birthday cases. Intermediate dime benefits
below are derived exactly; the source prints whole-dollar payments.

| Birth date | First month | PIA | Reduction months | Exact benefit | Whole dollars |
| --- | --- | ---: | ---: | ---: | ---: |
| 1935-05-31 | 1997-06 | 1207 | 35 | 972.30 | 972 |
| 1935-06-01 | 1997-06 | 1207 | 35 | 972.30 | 972 |
| 1935-06-02 | 1997-06 | 1207 | 36 | 965.60 | 965 |
| 1935-06-03 | 1997-07 | 1207 | 35 | 972.30 | 972 |
| 1935-12-31 | 1998-01 | 1232 | 35 | 992.40 | 992 |
| 1936-01-01 | 1998-01 | 1232 | 35 | 992.40 | 992 |
| 1936-01-02 | 1998-01 | 1266 | 36 | 1012.80 | 1012 |
| 1936-01-03 | 1998-02 | 1266 | 35 | 1019.80 | 1019 |
| 1937-12-31 | 2000-01 | 1372 | 35 | 1105.20 | 1105 |
| 1938-01-01 | 2000-01 | 1372 | 35 | 1105.20 | 1105 |
| 1938-01-02 | 2000-01 | 1410 | 38 | 1116.20 | 1116 |
| 1938-01-03 | 2000-02 | 1410 | 37 | 1122.10 | 1122 |

RS 00605.501's PIA-only examples are reproduced at the threshold interface,
because SSA supplies no earnings histories. $849.40 to $850.00 is only
$0.60 and is refused despite a whole-dollar increase; $850.40 meets $1.
The $445.50 December 1997 PIA with a $0.90 January 1998 increase remains
$445.50. December 1998's PIA is $451.20, and a $452.20 January 1999
candidate is accepted if there were 1998 earnings; without earnings it
remains $451.20. The inferred first candidate is $446.40.

An invented complete 35-year case has original AIME 100 and PIA $90.00.
Adding $420 earnings produces AIME 101 and $90.90, which is refused;
another $420 produces AIME 102 and $91.80, accepted against the PIA still
in force. With a 12-percent accrued COLA, $90.00/$90.90 become
$100.80/$101.80, so the $0.90 eligibility increase meets the actual $1 rule.
Other invented cases write every intermediate figure in their test
docstrings, including preserved 2020 bend points $960/$5,785 versus later
2021 points $996/$6,002 (AIME 1000: $876.80 versus $897.60).

CFR 404.284's 1979 example uses historical upward dime rounding. AIME 911
has raw PIA $395.92, rounded to $396.00; successive historical COLAs
9.9/14.3/11.2 percent give $435.30/$497.60/$553.40. These historical
arithmetic figures are pinned beside the modern API's explicit refusal.
The derived whole-dollar original is 432; the successive revised amounts
are 435/497/553, each explicitly asserted.
The legacy average-monthly-wage (AMW) example replaces $2,700 with $12,000,
giving $142,000 total versus the derived prior $132,700. Divisor 22*12=264
gives AMW $537 versus earlier $502, with supplied table PIA $407.70.
Historical COLAs give $448.10, $512.20 and
$569.60. Its initial $429.20 and table row are source-supplied inputs;
the captured material does not include the AMW table needed to
derive them. The modern API explicitly refuses that formula. The supplied initial
$429.20 is $21.50 above the $407.70 candidate. Applying the same historical
COLAs to the initial value produces $471.70/$539.20/$599.60, versus
$448.10/$512.20/$569.60 for the candidate. That is a $30.00 decrease by
June 1981, rather than an effective $1 increase. Tests preserve this
unexplained captured-source inconsistency side by side; no figure is
changed and no complete accepted recomputation is claimed. The captures
cannot settle whether the initial figure, table row or stated assumptions
need correction.
Tests also assert the derived whole-dollar amounts: 429 initially,
448/512/569 for the candidate and 471/539/599 for the original after COLAs.

## Readings taken and refusals kept

Ruling d1418 (Max, 2026-10-12) kept the three money-changing readings below
as named refusals until a population target needed them. Max's 2026-10-20
delegation makes each single reading the session's call under his
principles (P1 statute first; P2 regulations are law; P3 the agency breaks
true ties), logged in the source-conflict rulings; patterns and collisions
between principles go to him. This section records that pass (October 23,
2026). Each reading below names its basis; every remaining refusal keeps its
row and weight in the denominators.

RS 00615.015 says "In 2/1998 Demi has 37 RF." Its table and the same
example's payment text say "Demi - $1122 starting 2/2000". Tests pin both;
February 2000 produces the stated 37 months and $1,122.10/$1,122. This is a
source date erratum, not an altered monetary rule.

The reused float AIME floors zero for cent earnings $0.02, $2.07 and
$33.91 over three computation years: binary summation is
35.99999999999999 instead of exact $36. The exact guard yields AIME 1.
The executed counterexample was minimized over cent amounts; no two-year
cent-valued example summing $24 was found. This intended oracle divergence
is named `test_minimized_cent_earnings_float_aime_boundary_is_intended_correction`.
Python's ties-to-even bend-point rounding also differs from the statute at
an exact half dollar; the named tie test pins the statutory upward result.
These are arithmetic diagnostics, not competing statutory interpretations:
the Act's own rounding rules decide both.

### Reading taken: spouse reentitlement before FRA

Source conflict `us:oasdi-arf-spouse-reentitlement-credits` (P1, statute
first). RS 00615.201A.1 says "After 12/72 a spouse reentitled prior to FRA
as a spouse on the same earnings is reduced the same number of months as
the earlier entitlement. An ARF at FRA will remove all months of
nonentitlement." RS 00615.491A says "Beginning in 1/78, if a reduced spouse
is terminated and then reentitled, (months in which the spouse's benefits
were terminated will be eliminated from the reduction factor when the
spouse is reentitled." The unmatched parenthesis is present in the captured
.491 text.

The Act settles the timing. Section 402(q)(1)(B)(i) reduces each month
before retirement age by "the number of months in the reduction period for
such benefit (determined under paragraph (6)), if such benefit is for a
month before the month in which such individual attains retirement age".
Clause (ii) substitutes the adjusted reduction period, which (q)(7)(C)
shortens by "any month for which such individual was not entitled to such
benefits because of the occurrence of an event that terminated her or his
entitlement to such benefits", only "if such benefit is (I) for the month
in which such individual attains age 62, or (II) for the month in which
such individual attains retirement age". A spouse's reduction period begins
with the first month of the original certificate ((q)(6)(A)(ii)), which
remains effective "for the month in which it is filed and for any month
thereafter" ((q)(5)(B)(i)). RS 00615.201A.1 states this timing; .491A's
removal at reentitlement departs from it and is not followed.

For an invented birth on January 2, 1960, first reduced entitlement in
January 2022, termination in February 2022, reentitlement in March 2022,
unreduced benefit $650 and FRA in January 2027, the reduction period has 60
months. March 2022 through December 2026 pay $422.50 ($422). The January
2027 ARF removes February 2022, leaving 59 months and $425.20 ($425). The
.491A reading would pay $425.20 from March 2022, $2.70 a month more. The
former refusal `arf_spouse_reentitlement_before_fra` is withdrawn, with its
reason value. `test_spouse_reentitlement_takes_the_statutory_timing` pins
the statutory quotes and both amounts;
`test_spouse_reentitled_before_fra_keeps_original_months_until_fra` pins the
public API; the Hypothesis property
`test_reentitled_spouse_keeps_original_months_until_fra` checks, for any
terminated history and any pre-FRA month, that the payment equals the
never-terminated claim and G's 60-month spouse reduction with zero
tolerance, and that the FRA adjustment credits exactly the terminated
months, so the benefit cannot fall at FRA.

### Refused: widow(er) FRA for births January 2, 1911 through January 1, 1912

Source conflict `us:oasdi-survivor-fra-1911-births` (refusal kept; it cannot
change a computed amount). RS 00615.003 says "People Born Before 1/2/1911"
and "FRA for widow(er)'s benefits was age 62", then "People Born from
1/2/1911 Through 1/1/40" at age 65. CFR 404.409 says "Before 1/2/1912 62
years." and "1/2/1912—1/1/1940 65 years."

A widow(er) of this cohort has a reduced benefit only if first entitled
before full retirement age, which the cohort attains during 1973 under FRA
62 and during 1976 under FRA 65. Both precede January 1978, which
`arf_initial_entitlement_before_1978` refuses independently; entitlement
from 1978 falls after both ages and has no reduction months. The FRA helper
must return one month, so it still refuses the cohort by name, and
`apply_arf` keeps the same reason. Should a pre-1978 path ever be built, the
Act points to POMS's boundary: Pub. L. 92-603 §102(i) applies the 1972
widow amendments "with respect to monthly benefits ... for months after
December 1972", and a birth on January 2, 1911 attains 62 on January 1,
1973. (The provision is excerpted from the statutory notes of the same
LII 42 U.S.C. 402 body pinned in this module's manifest, in
`lii_usc_402q_415f_excerpts.txt`.) The regulation's January 2, 1912 boundary would then be a regulation
at odds with its statute, which P2 returns to Max. An invented January 2,
1911 birth claiming January 1973 with PIA $1,000 gives $829 under FRA 65
(36/60 of 28.5 percent) versus $1,000 under FRA 62; that claim is outside
the supported window under either reading.

### Refused pending Max: nonbinding widow(er) child-in-care months

Source conflict `us:oasdi-arf-widow-child-in-care-credits`. CFR
404.412(a)(4) credits "any month in which she or he had in her or his care
a child of the deceased insured individual and for which the child was
entitled to child's benefits". RS 00615.482 instead specifies "widow(er)'s
benefits were increased to the mother or father's rate." The Act
402(q)(7)(D) refers to "any month in which the reduction in the amount of
such benefit was determined under paragraph (5)(D)", the mother/father
floor, while (q)(7)(B) gives wife's and husband's benefits the plainer test
"any month in which such individual had in his or her care ... a child of
such person entitled to child's insurance benefits". Congress used
different words for widows. On the better reading the Act and SSA's
manual credit only months in which the floor set the benefit, while the
regulation copies the wife's wording and credits every caregiving month.
A broader reading of "determined under paragraph (5)(D)" is arguable:
(5)(D) is applied in every caregiving month, even when it does not bind,
and on that reading the three sources could be harmonized.

So the regulation may reach past its statute. P2 returns such a case to
Max, and whether P2 covers SSA's 20 CFR at all (it names Treasury
regulations) is itself unruled, so both are queued together as decision
d1920, recommending the narrower statutory reading. Until he rules, the supported input
certifies actual mother/father-rate months and a nonbinding caregiving
history keeps the named refusal. At age 64, FRA 67, PIA $1,000, 36/84 of
28.5 percent gives $877.80; crediting six nonbinding caregiving months
under the regulation gives $898.20, $20.40 a month more. Both
counterfactual amounts and the explicit refusal are tested.

The $1-after-COLAs rule is settled expressly by RS 00605.501. Historical
upward rounding is different law, not a source erratum. No choice between
these rules is left implicit.

## Monthly assembly inputs

I must supply original benefit-record identity, benefit kind, exact date of
birth, original reduced-entitlement/election month, certified final work
deductions separated from provisional suspensions, and explicit category
credits. It must declare exceptional histories, maintain complete dated
entitlement and termination state, apply any current child-in-care payment
floor separately, and adjust the spouse's own benefit independently. For a
deceased worker it supplies date of death; hypothetical ARF does not imply
payment in or after the death month.

Recomputation needs the established eligibility year, original indexing
year and computation count, original bend points, eligibility-level PIA in
force, complete annual earnings from 1951 with unavailable years marked,
annual December COLA percentages including explicit zeros, entitlement
window, and death/FRA months. I supplies the earnings-year cutoff and must
retain each result's effective date. Death-year annual earnings may include
amounts paid after death (CFR 404.282); this is retrospective statutory
recomputation, not permission to use later-year earnings early.

Both modules are added to the historical birth-evidence exclusions and the
matching disjointness test. They remain opt-in references and are not
reachable from the frozen historical projection.

## Not in scope

No real microdata, population pipeline, claiming behavior, forecast,
monthly calendar assembly, final deduction calculation, automatic SSA
notices, processing-payment dates, family-payment monotonicity, disability
freeze or conversion machinery, AMW, old-start, guarantee and minimum formulas,
reopening, judicial review, death-before-FRA alternative computation, or
unsupported widow/spouse histories are admitted. Refusals block dependent
results until a separately sourced implementation exists.
