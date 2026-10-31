# Track B G: the gross-benefit layer

**Verification class: statutory conformance. Admitted scope: gross monthly
benefits for supported invented or published statutory cases only; no
population, behavioral or forecast claim.**

**Status: build-only, 2026-09-29; statutory delayed-credit convention
(#494), 2026-10-11; review fixes through 2026-10-25. No real-data
computation.** Inputs are invented families and SSA's published worked
examples.

The Track B design lives outside this repository, at
`microcosm-launch-evidence/dynasim-parity-20260909/trackb-design-20260928.md`
(revision 3, SHA-256 prefix `6fd6f4aa5a83da80`). Its §3.1 row G asks for "family
maximum, age and dual-entitlement reductions, monthly family payment;
unsupported family configurations flagged", verified by "statutory worked
examples, Python reference cases, and an Axiom differential where a pinned
rule exists". §3.2 gives G the verification class **statutory conformance**
and admits "gross benefits for supported family configurations only". Max's
ruling d515 (2026-09-28) adopted §10 question 9's default: a Python reference
now, with Axiom differentials as diagnostics once a pinned rule exists.

- Code: `src/populace_dynamics/track_b/gross_benefits.py`.
- Tests:
  - `tests/test_track_b_gross_benefits.py` covers the worked examples,
    boundaries, households, the 403(a)(5) guard and refusals.
  - `tests/test_track_b_gross_benefits_properties.py` holds the Hypothesis
    invariants and the differentials against `ss/benefits.py`,
    `ss/statutory_delayed_credit.py` and the sealed ledger's rounding.
  - `tests/test_track_b_gross_benefits_oracle.py` checks the policyengine-us
    bundle (skipped without a checkout).
- Sources: `tests/data/track_b/gross_benefit_sources/`. The manifest pins each
  URL, UTC retrieval time, byte count and SHA-256.

## Input boundary and threat model

Every public argument and declaration field declares a schema. Scalar
values must have the exact built-in declared type (`type(x) is T`); `bool`
is not an integer. Number encodings retain their documented conversion to
owned built-in `Fraction` values. Enum values must be canonical members of
the declared enum, compared by identity. Declarations must have the exact
declared Track B class and are rebuilt field by field through that schema.
Every nonmapping collection slot declares either ordered-sequence or
unordered-membership semantics. An ordered slot accepts exact built-in
`tuple` and `list` values and snapshots every element, in order, into a
tuple. It rejects `set` and `frozenset`: order and multiplicity cannot be
recovered from an unordered container. A membership slot accepts exact
built-in `tuple`, `list`, `set` and `frozenset` values and normalizes to a
frozenset after checking every raw element. Dictionaries
must yield exactly their length in distinct valid keys. Subclasses,
`__class__` impersonation, custom mappings and iterators are input errors.
For compatibility with R1's immutable parameter declarations, its read-only
mapping views are unwrapped only when their backing object is an exact
built-in dictionary; that dictionary then follows the same schema.

Every raw dictionary key and value is checked before constructing the
snapshot. Monetary histories and keyed record or share mappings retain
their key-value associations; they are not membership sets. Normalization
must not collapse distinct raw keys. The declared `compute` slot uses
`callable()` and preserves the callback object, including callable
dataclasses. Callback results still require the proper layer's computation
seal. Each public call validates and detaches
its inputs once; private helpers compute on that owned snapshot. Derived
statutory rates belong to that snapshot only. No caller-object identity
cache carries validation across calls, so mutation between calls is checked
again. Invalid inputs create no denominator row.

An evaluator checks provenance: a value was computed by its own Track B
layer, has an unaltered declared payload, and has the right layer and type.
It does not check freshness or attribution. A callback may return a genuine result computed
earlier or re-raise a genuine refusal computed earlier. The supported
result counts as supported; the refusal counts with its own reason. Which
family the caller assigns that value to is the caller's declaration, just
like the key and weight. The evaluator cannot independently verify those
declarations. Track B guarantees that only values it computed enter a
denominator and that every value entering its functions passes its schema.

This is a public API contract. It makes no claim about code that reaches
private implementation names, monkeypatches modules, or mutates an input from another
thread during a call. Statutory amounts, coverage refusals, source captures
and worked-example figures are unchanged. The strict container contract
supersedes the earlier acceptance of one-shot iterators and the acceptance
of sets in ordered slots. These are representation narrowings, not new
statutory readings. Equivalent built-in list controls retain their amount
and refusal assertions.

Executed boundary invariants are: exact type and enum-member admission;
validation of all raw container members before hashing; invalid-before-
refusal precedence with zero denominator rows; callback preservation and
sealed-result checking; one parameter snapshot per public family call;
and revalidation after mutation between calls. The schema-wide Hypothesis
checks and reviewer counterexamples are in
`tests/test_track_b_input_schema.py`. Existing statutory, rounding,
monotonicity, order-independence and denominator invariants below remain in
force. No new statutory interpretation is introduced by this boundary.

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
methods and dunders, checks the exact registered receiver
type and its argument schemas before attribute access or protocol use.
Seal validation begins with this exact-type check. A foreign receiver or
argument whose hooks raise a genuine refusal remains `InvalidFamilyInput`,
with zero hook calls and zero denominator rows. Genuine sealed results
retain their existing seal checks. The five savings-clause guard getters
retain their valid values and one receiver-schema entry per getter.

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
| `WorkerRecord.cola_percents`; `increase_by_colas.percents` | Ordered events. Act 215(i)(2)(A)(ii) floors after each increase, so both order and repeated equal increases affect money. |
| `HouseholdRecord.beneficiaries`; `family_benefits.beneficiaries` | Ordered rows. Preserve every declaration so duplicate identities still produce their input error rather than disappearing. |
| `count_family_outcomes.outcomes`; `weighted_record_total.outcomes`; `weighted_mean_record_total.outcomes` | Ordered observations. Preserve every row so duplicate outcome keys remain input errors; distinct keys retain every count and weight. |
| `RecordState.deferred_refusal` | Ordered fixed pair of reason and detail; the two positions have different types and meanings. |
| `Beneficiary.conditions`; `WorkerRecord.conditions`; `RecordState.conditions` | Membership of canonical condition enums. Repeating the same condition changes neither money nor refusal precedence. |
| `SSAParameters.pia_factors`, `early_monthly_rates`, `spousal_early_monthly_rates`, `fra_months_by_birth_year`, `delayed_credit_by_birth_year`, including each schedule pair | Ordered bracket arrays and schedules. Positions and increasing year order determine the applicable rates; no entry may silently disappear. |
| `FamilyBenefits.beneficiaries` (computed output) | Ordered beneficiary results, preserving every row. |
| `december_cola_percent`, parameter `nawi` and `wage_base`, redistribution mappings, household `records` and `guards`, and computed record/reason mappings | Keyed associations in exact dictionaries or checked computed mapping views. Each raw key and value is validated; normalization collisions are rejected. The count/weight value in a reason mapping is an ordered fixed pair. |

No membership field carries an amount, an event count or a weight.
Canonical flags have no alternate numeric encodings. The R2/R3 inventories
below additionally admit exact calendar months; equivalent representations
identify the same month and cannot create a second statutory credit.

The invented reviewer witness `increase_by_colas(1, [10, "10"])` remains
$1.20: the first increase gives $1.10 and the second is dime-floored from
$1.21. Starting from $100 gives $121. Both set forms are now input errors,
including mixed integer, text, Fraction, Decimal and float encodings. This
is the same per-event rounding already required by Act 215(i)(2)(A)(ii),
not an additional published worked example.

`tests/test_track_b_gross_benefits_fix_round_15_collections.py` executes:

- `test_ordered_colas_equal_the_element_by_element_dime_fold`: Hypothesis
  compares each ordered COLA input with an independent per-element fold.
- `test_denominator_sequences_preserve_duplicate_key_errors`: Hypothesis retains
  duplicate-key input errors instead of silently collapsing repeated rows.
- `test_every_collection_schema_declares_order_or_membership`,
  `test_every_collection_field_has_canonical_container_semantics` and
  `test_every_public_collection_argument_preserves_its_declared_semantics`:
  every nonmapping schema declares its kind and uses its canonical output
  container without dropping ordered elements.
- `test_membership_months_collapse_equivalent_month_encodings`,
  `test_membership_fields_contain_only_months_or_canonical_flags` and
  `test_membership_numeric_aliases_are_rejected_not_collapsed`: membership
  normalization preserves calendar meaning and rejects undeclared aliases.

`tests/test_track_b_gross_benefits_fix_round_15_receivers.py` executes the
receiver/argument-before-hooks invariant with
`test_review_four_layer_getter_rejects_receiver_before_any_hook` and the
Hypothesis `test_every_public_reader_rejects_foreign_receiver_without_hooks`.
`test_evaluator_accepts_precomputed_genuine_result_with_declared_metadata`
and `test_evaluator_counts_reraised_genuine_refusal_with_its_own_reason`
pin both genuine-precomputed composition behaviors. These boundary
properties supplement, rather than replace, the statutory invariants below.

## What it computes, in statutory order

For one worker's record and one benefit month:

1. **Family maximum.**
   - Retirement and survivor records use 403(a)(1)-(2). The three bend points
     are $230, $332 and $433 times NAWI(year - 2) / NAWI(1977), rounded to the
     nearest dollar with 50-cent ties up (215(a)(1)(B)(iii)).
   - The rates are 150, 272, 134 and 175 percent of the PIA for the year of
     first eligibility, before COLAs (RS 00615.736A.1). The total is floored to
     the dime.
   - Disability records use 403(a)(6) when initial DIB entitlement came after
     June 1980 (RS 00615.740-.742). The maximum is min(max(85% AIME, PIA),
     150% PIA).
   - 403(a)(6) itself states no rounding. The disability maximum is floored to
     the dime; the source is below, under "Disability-maximum rounding".
   - COLAs then raise the PIA and the maximum alike, dime-floored after each
     increase (215(i)(2)(A)(ii)).
2. **Original benefits (OB).**
   - Spouse 1/2; child 1/2, or 3/4 after the worker's death; widow(er) 100
     percent; mother or father 3/4. Each OB is dime-floored.
   - A widow(er)'s OB uses the PIA as determined under 202(e)(2)(B)-(C): the
     windexed PIA, or the PIA deemed equal to the deceased's credit-increased
     benefit.
3. **Reduction for the maximum** (403(a)(4); RS 00615.756).
   - Each OB is scaled by available / total OB and dime-floored. No share can
     exceed its OB.
   - In a life case the worker's PIA is deducted from the maximum first. The
     deduction is the PIA, never the credit-increased benefit (RS 00615.695).
   - Divorced spouses and surviving divorced spouses are paid outside the
     maximum. Everyone else is computed as if they were not entitled
     (403(a)(3)(C); RS 00615.680-.682).
4. **Dual-entitlement redistribution** (RS 00615.768, the Parisi rule).
   - This applies to benefits payable for October 1999 or later.
   - Other auxiliaries are reduced only by what a dually entitled beneficiary
     is actually paid before age reduction. The rest of the maximum is
     redistributed to them, capped at each OB.
   - If every beneficiary subject to the maximum is dually entitled, the rule
     is disregarded.
5. **Age reductions after the maximum** (RS 00615.210, .754A.1, .301B.1.c).
   - Spouse: exact 1/144 per month for 36 months, then 1/240 per month,
     dime-floored (RS 00615.201).
   - Widow(er): the 28.5 percent maximum spread over the reduction period, with
     the reduction amount rounded *up* to the dime (RS 00615.301).
   - The widow(er) period is one of 60, 62, ..., 84 months, even without a
     birth cohort. A known cohort fixes exactly one of those periods
     (RS 00615.301B.2).
   - The RIB-LIM applies next (402(e)(2)(D); RS 00615.320).
   - A widow(er) with an entitled child in care receives at least what a
     mother or father would receive after the maximum, when that is larger
     (RS 00615.340; .010). The comparison uses the mother/father 75-percent
     OB under 202(g)(2), its maximum share and any settled dual-entitlement
     redistribution; the actual widow's own-benefit offset follows.
6. **Dual entitlement** (402(k)(3)(A)). The auxiliary benefit is reduced, but
   not below zero, by the own benefit after 402(q).
   - An aged spouse entitled to the own benefit in or before the spouse
     benefit's first month uses method C (402(q)(3)(B)/(C); RS 00615.250).
     Only the excess over the own PIA takes the spouse reduction. Delayed
     credits on the own RIB follow RS 00615.694.
   - A spouse entitled first, with the RIB later, uses method B
     (RS 00615.240). The spouse benefit keeps its 402(q)(1) reduction and is
     paid in excess of the RIB.
   - The caller must say which came first (`own_benefit_first`) for every
     dually entitled aged spouse or divorced spouse. Current-care divorced
     spouses with own RIB do not require this order. There is no default
     for aged methods: in the
     RS 00615.240 example the two methods pay $250.00 and $262.50.
   - Supported widow(er)s use method B: both benefits are reduced
     independently (402(q)(3)(E); RS 00615.020A.3). G's own-RIB widow
     support begins at cohort 1929, a deliberately narrower implementation
     boundary than the source's January 2, 1928 boundary; see below.
   - A spouse with a child in care is never reduced for age (402(q)(5)(A)(ii))
     and is paid the excess over the reduced RIB (RS 00615.020A.3 note).
     RS 00615.010/.201A.2 explicitly include a divorced spouse with current
     care; that spouse keeps its 403(a)(3)(C) outside-maximum status.
   - A spouse is not entitled when the own PIA is at least half the worker's
     PIA (202(b)(1)(D)).
   - A widow(er) is not entitled when the own RIB is at least the deemed PIA
     (202(e)(1)(D)).
   - A mother or father is not entitled when the own RIB is at least 3/4 of
     the PIA (202(g)(1)(C)).
7. **Monthly family payment.** Amounts stay exact dime multiples. 215(g) rounds
   each monthly benefit down to a dollar. "Gross" means before 203(b)
   earnings-test deductions and the 1840(a)(1) Medicare premium.

All arithmetic uses exact fractions: SSA's instruction is that decimal
equivalents "often" give an answer 10 cents lower (RS 00615.005B). Statutory
rates are cross-checked against the repository's policyengine-us bundle and
then used as exact fractions. NAWI, full retirement ages and the 402(w)
credit schedule come from that bundle.

## Why G reimplements the worker and auxiliary arithmetic

Design §6 suggests reusing the existing worker and auxiliary primitives in
`ss/benefits.py`. G does not: it recomputes the 402(q) reductions, the
402(w) credits and the auxiliary shares in exact fractions. The reasons:

- **POMS requires exact computation.** RS 00615.005B tells SSA staff to use
  the fraction, not its decimal equivalent, because the decimal "often"
  lands 10 cents lower. `ss/benefits.py` works in floats over
  policyengine-us's stored decimals (`0.00555556` for 5/9 of 1 percent).
- **The float path lands a dime low in 3.46 percent of cells.**
  `test_float_ledger_dime_errors_counted_exhaustively` covers every PIA
  from $0.10 to $557.20 by dime with 1-60 reduction months: 334,320 cells.
  `floor_to_dime` over `early_reduction` lands a dime low in 11,572 of
  them and never high. POMS's $802.80 example is low in the wider one-off
  count; it is outside the 334,320-cell ledger's PIA range.
- **The sealed oracle keeps its legacy delayed-credit cap.**
  `ss.benefits.delayed_credit` remains byte-identical because the
  first-estimates birth-evidence source seal binds it to the reviewed
  implementation. Its standard bundle limits credits to 48 months, which
  is short for births 1917–1942. The sibling
  `ss/statutory_delayed_credit.py` uses the full `840 - FRA` window and
  agrees with G over that whole window. G retains exact fractions and its
  validation of increment months; the new float function truncates claims
  after 70. `DelayedCreditWindow` names the statutory and sealed legacy
  conventions explicitly.
- **Its survivor path has one reduction period per parameter bundle.** The
  default spreads the widow(er) reduction over 84 months, exact only for
  survivors born 1962 or later (`ss/params.py`). G takes each widow(er)'s
  period as an input, and `widow_reduction_period_months` implements the
  RS 00615.301B.2 birth-date table.

The differential tests keep these implementations aligned over their
shared surfaces. The reduction fractions, `spousal_benefit` and
`widow_benefit` in `ss/benefits.py` agree with G within documented rounding.
Its sealed delayed-credit function agrees through `min(48, window)`;
the new statutory float function agrees over the whole FRA-to-70 window,
including months past 48 for births 1917–1942 (#494). A named pin preserves
the sealed legacy result rather than treating that retained convention as
an open bug. These are invariant 10 below. The exact monetary
reimplementation needs Max's ratification, because §6 asked for reuse.

## Delayed credits

402(w)(2)(A) counts increment months from the month of attaining full
retirement age to the month before attaining 70. So a cohort can earn at
most `840 - FRA` months.

- The window is 60 months for births 1917-1937 (FRA 65), and 58 down to 50
  months for 1938-1942. It is 48 for 1943-1954, 46 down to 38 for
  1955-1959, and 36 from 1960.
- `test_delayed_credit_window_matches_the_poms_chart_for_every_cohort`
  reads the RS 00615.692E chart from its capture. For every birth year from
  1917 to 1960 it checks the FRA, the monthly rate, the window, and that G
  accepts the whole window and rejects one month more.
- More months than the window is `InvalidFamilyInput`, wherever the months
  enter: `worker_age_adjusted`, an `OwnBenefit`, a `WorkerRecord` (checked by
  `record_state`), or a `RecordState` given directly (checked by
  `family_benefits`).
- The bundle's `max_delayed_months` (policyengine-us `max_delayed_years: 4`,
  so 48) is not used. It is short for births 1917-1942, and the FRA-to-70
  window bounds every later cohort anyway. The new
  `ss.statutory_delayed_credit.delayed_credit` also ignores it. The sealed
  `ss.benefits.delayed_credit` retains the captured bundle's cap by design.
  The statutory float function accepts months from FRA to entitlement, so
  a claim after 70 earns the window credit. G accepts already-counted
  increment months and rejects more than the window. Tests pin both input
  conventions and both named oracle conventions.
- Credits for births before 1917 are refused
  (`delayed_credits_born_before_1917`). 402(w)(6)(A) gives 1/12 of 1 percent a month to a person first eligible
  before 1979. The bundle, like policyengine-us, starts its schedule at 3
  percent a year. RS 00615.692E also shows windows past 60 months for
  births before 01/02/1914. Retired workers on in-scope records are
  unaffected, because eligibility from 1983 implies a birth after 1917. A
  spouse's own RIB can reach the refusal.
- Birth years follow SSA's bands, which run from January 2 to January 1. A
  person born on January 1 takes the previous year.

## Disability-maximum rounding

403(a)(6) states no rounding for the disability maximum. G floors it to the
dime on two sources, both in the Social Security Bulletin 75(3) capture:

- the rules paragraph: "The final amount is rounded to the next lowest ten
  cents";
- the Table 2 note: amounts "would actually be rounded down to the nearest
  dime".

After that, 215(i)(2)(A)(ii) floors every COLA increase of the maximum to the
dime. The captured POMS sections on the disability maximum (RS 00615.740 and
.742) say nothing about rounding. Both quotes are pinned by
`test_worked_example_figures_are_quoted_from_the_captures`. The Bulletin is
an SSA research publication, not a program instruction, so resting the
rounding on it needs Max's acceptance.

## Households and the entry point

A family that draws on more than one record cannot be computed one record
at a time. `household_benefits` computes every record together;
`household_month_outcome` adds one monthly guard per record. Both use the
household checks exposed by `check_household_records`, validating all
family inputs before coverage refusals. The household checks do three things:

- A child entitled on two or more records raises `combined_family_maximum`,
  because 403(a)(3)(A) may combine the maximums (RS 00615.770).
- Anyone else entitled as an auxiliary or survivor on two or more records
  raises `multiple_auxiliary_records` (RS 00615.768A).
- A living worker who is also an auxiliary on another record must declare
  that record's RIB or DIB as `own_benefit`. The check compares kind, PIA,
  reduction months, credits and every supplied birth year. One person has
  one cohort across their worker record and all beneficiary rows
  (402(q)(6); RS 00615.003/.010). A known year is carried into immutable
  copies of every occurrence before family validation and calculation;
  missing duplicate metadata does not erase it. `RecordState.worker_birth_year`
  preserves the insured person's cohort for every record kind, including
  an eligible worker who has not claimed. Own-benefit entitlement determines
  whether a RIB or DIB must be declared; it does not determine whether the
  person's known cohort constrains another record. A mismatch, a worker with
  two records, or a deceased worker entered as a beneficiary raises
  `InvalidFamilyInput`.

`family_benefits` computes a single record only when the caller passes
`standalone=True`. That is the caller's statement that no beneficiary is
entitled on another record, and that a worker who is an auxiliary elsewhere
has declared that benefit. It is meant for SSA's single-record examples and
tests. Without it the call is a `TypeError`, and `standalone=False` is a
`ValueError` that names `household_benefits`. So "never default to
single-worker cases" holds at the API: a one-record computation happens only
by declaration.

Input errors are raised before any coverage refusal, in the household and
in every record's family. Input errors include:

- delayed-credit months past 70;
- a missing entitlement order;
- a payment month before the record's eligibility year or first DIB
  entitlement;
- a duplicate beneficiary id;
- a role the record cannot have;
- a widow(er) reduction period outside 60, 62, ..., 84, or a period that
  differs from a known cohort;
- conflicting worker-record/beneficiary/own-benefit birth years, or reduction
  months outside the one cohort known from any record (402(q)(6);
  RS 00615.003/.010);
- `child_in_care` that does not name an entitled child on this record for
  the payment month.

This ordering means `evaluate_family` can never count an invalid row as a
coverage gap. `InvalidFamilyInput` propagates out of `evaluate_family` by
design. The aggregate stops, with no outcome to drop or half-count, and a
household with one bad record returns nothing at all.

## 403(a)(5)

The statute (captured in `ssa_act_203`) applies when two or more persons are
entitled for a month, the maximum applies to their benefits, and the PIA is
increased for the following month. That month's total is then treated as
increased by the smallest amount that keeps the total "for any such
subsequent month" from falling below it. Both totals are after 403(a) and
402(q). The guarantee is not limited to the next month. RS 00615.801B.2
adds that a saving clause, once established, "will continue in effect
until the table or formula maximum becomes larger", and may become payable
again.

The following describes the explicit `LITERAL_REFUSAL` alternative retained
from G v2. The default is now `SSA_OPERATIONAL`, implementing d1338 and the
RS 00630.400 procedures detailed in "Operational saving clause, October 23,
2026" below. `SavingsClauseGuard` carries the chosen reading across one
record's months:

- **It protects the total of a qualifying month.** A qualifying month has
  two or more persons entitled, a binding maximum, and a higher PIA the next
  month. The highest protected total is carried forward. RS 00630.400
  states SSA's version of this condition as "Benefits for that month are
  reduced for the MAX" (its 1972 Family Payment Saving Clause).
- **It refuses any later governed month whose total falls below the protected total**
  (`savings_clause_403a5`), whether or not the PIA rose into it. It also
  refuses every later governed month after that one, because the clause stays in
  effect.
- **It refuses every later governed month once a protected total may exist that G
  cannot see** (`savings_clause_history_unknown`). That covers:
  - a path that does not start at the record's first month of entitlement;
  - a month G refused for another reason while a protected total was in
    force;
  - a refused month followed by a PIA increase, or given without its PIA.
- **It computes a month in which nobody is subject to the maximum.**
  403(a)(4) decreases only benefits other than the worker's own, so there is
  nothing to raise. Such a month's total still counts. If it is below the
  protected total, the clause takes effect for later months.

Each refused month is a `FamilyOutcome` with its reason, so it stays in every
denominator. The review's counterexample is the unit test
`test_savings_clause_protects_every_later_month_not_just_the_next`:

1. November: $1,000 PIA and two children at $250, total $1,500.00.
2. December: a 2.5 percent COLA. PIA $1,025.00, maximum $1,537.50, children
   at $256.20, total $1,537.40.
3. January: no PIA increase. An aged spouse reduced for 60 months joins.
   Children at $170.80 and the spouse at $111.00, total $1,477.60.

A check of consecutive months alone passes both pairs. The guard refuses
January and every month after it. Two property tests restate the contract
independently:

- `test_savings_clause_guard_along_month_paths` runs random paths of COLAs,
  arrivals and departures.
- `test_a_reduced_joiner_after_a_cola_is_refused_iff_the_total_falls`
  generalizes the counterexample.

With the statutory maximum, a COLA can trip the guard even for families
that are not dually entitled. A COLA raises the maximum by at least as many
dimes as the PIA, so the room left for auxiliaries never shrinks. The
separately dime-rounded proportional shares need not have a monotone sum
(215(i)(2)(A)(ii); 403(a)(4); POMS RS 00615.756). The property
`test_formula_maximum_colas_preserve_available_room_and_guard_contract`
checks the available room and the actual 403(a)(5) contract: a qualifying
PIA increase followed by a lower total is refused, with its full row and
weight retained; otherwise the month is admitted. Its survivor generator
includes parents.

**Known over-refusals.** Each is conservative and inflates the unsupported
rate:

- **Any fall after any protected month, at any later time.** A beneficiary
  leaving six months after a December COLA triggers refusal of every later
  governed month on the record, including a widow month the next year. In
  `test_known_over_refusal_a_beneficiary_leaves_in_a_cola_month`, two of
  three children leave in December and the total falls from $1,750.00 to
  $1,537.50. G refuses December. No captured source says whether a change of
  membership triggers the clause.
- **A month in which the maximum does not bind.** 403(a)(4) only decreases
  benefits, so on the statute's text a larger maximum changes nothing there.
  But SSA's procedure in RS 00630.400 divides the protected payment among
  the auxiliaries without mentioning the OB cap.
- **Every governed month after a refused month** while a protected total is in force.
- **Every governed month of a path with unknown history.** A simulation that starts
  with families already on the rolls must either reconstruct each record
  from its first month of entitlement or accept these refusals.

RS 00630.400's summary also requires "at least one beneficiary is reduced for
age". G does not require it, which can only add refusals.

Needs Max's judgment: the literal 203(a)(5) guarantee that totals "for any
such subsequent month will not be less" reaches later composition changes.
RS 00630.400's operational condition instead states "Total family payment
is less after the PIA increase than it was before." Its additional condition
is "Benefits for that month are reduced for the MAX and at least one
beneficiary is reduced for age;". In the invented three-child case above,
two children leaving in the COLA month lowers the total from $1,750.00 to
$1,537.50. The literal reading refuses; the operational reading admits that
$1,537.50 total when no beneficiary is reduced for age. This module keeps
the literal refusal.

Ruling d1418 (2026-10-12): keep the current defaults; reopen any one when a
population target needs it.

Ruling d1338 (2026-10-12): adopt SSA's operational reading (RS 00630.400),
keeping the literal reading behind a switch; implemented in G part 2.
Until then this module applies the literal refusal.

## Supported and refused configurations

| Record | Supported beneficiaries |
| --- | --- |
| Retirement (living worker on RIB, with any reduction or credits) | Aged spouse, spouse with child in care, divorced spouse with settled current care or aged history, child |
| Disability (worker on DIB, entitled after June 1980) | The same |
| Survivor | Aged widow(er), disabled widow(er) from January 1984, surviving divorced spouse, mother or father, child, one or two parents |
| Retirement, eligible living worker not entitled (from January 1985) | Independently entitled divorced spouses only; no worker payment |

These role families are supported when inputs are valid and none of the
refusals below applies. Invalid inputs raise `InvalidFamilyInput` before
coverage refusals. Valid unsupported configurations raise
`FamilyConfigurationUnsupported` (code `FAMILY_CONFIG_UNSUPPORTED`, design §7).
G never falls back to a single-worker computation.

| Reason | Trigger |
| --- | --- |
| `eligibility_before_1983` | Pre-June-1982 maximums rounded up (RS 00615.736B.3); pre-1979 table maximums |
| `payment_month_before_1983` | Months outside the post-May-1982 rounding rules |
| `di_entitlement_before_july_1980` | The pre-1980 disability maximum |
| `combined_family_maximum` | A child entitled on another record (403(a)(3)(A)), declared or found by the household check |
| `multiple_auxiliary_records` | Anyone else entitled as an auxiliary or survivor on two records (household check) |
| `deemed_or_putative_spouse` | 403(a)(3)(D) |
| `parent_benefit` | More than two declared parents, or the circular own-RIB entitlement interval for two potential parents (RS 00209.001/.015) |
| `disabled_widow_before_1984` | DWB payment months before January 1984 (RS 00615.310B.1/B.3) |
| `dib_guarantee_pia` | RS 00615.736B.2, .738 |
| `dib_after_reduced_rib` | 402(q)(2) |
| `workers_compensation_offset` | Section 224 |
| `government_pension_offset` | 202(k)(5), only benefit months through December 2023 |
| `administrative_finality` | Protected rates (RS 00615.754A.3) |
| `dual_entitlement_sequence` | A spouse's DIB after the spouse benefit (RS 00615.260), an aged widow(er) with DIB, an own-RIB widow(er) before G's cohort-1929 implementation boundary (the source's method-D boundary is January 2, 1928; RS 00615.010/.020B), or DWB with own RIB or DIB |
| `parisi_redistribution_ambiguous` | Own delayed credits, an actually limiting RIB-LIM after maximum and age reduction, or dual zero reached only after auxiliary age reduction remain unsettled by GN 02603.050A/C |
| `parisi_before_october_1999` | A binding maximum with dual entitlement before 10/99 |
| `independently_entitled_divorced_spouse` | IEDS before January 1985 or a WEP-affected worker record before January 2024 (RS 00202.100) |
| `non_aime_formula_pia` | Old-start, special-minimum and frozen-minimum PIAs (RS 00615.740B.1) |
| `savings_clause_403a5` | Under explicit `LITERAL_REFUSAL`, a governed month whose total fell below a 403(a)(5) protected total, and every later governed month |
| `savings_clause_membership_change` | Membership or record kind changes during a carried operational protection; the capture supplies no successor protection rule |
| `savings_clause_rate_procedure` | An operational raise needs an uncaptured survivor/dual/deduction/reduced-auxiliary allocation, a simultaneous age-factor change or declining FMAX prevents causal attribution, or the protected rate exceeds OB; the captured procedure does not settle these payments |
| `savings_clause_history_unknown` | A month for which a protected total G cannot see may exist (a path not started at entitlement, or a month G did not compute) |
| `widow_drc_savings_clause` | A May 1978 beneficiary protected from widow(er) deceased-worker DRC reductions (RS 00615.712) |
| `widow_drc_savings_clause_history_unknown` | A widow(er) subject to the maximum has an OB that may include deceased-worker delayed credits, another beneficiary is subject to the maximum, and neither an explicit exclusion nor complete first-ever DIB history rules out May 1978 protection (RS 00615.712; .736B.2b) |
| `widow_child_in_care_unknown` | A widow(er), including a disabled widow(er) or surviving divorced spouse, and an entitled child are on the record without a current-month care attestation (RS 00615.340; .010) |
| `divorced_spouse_child_in_care_unknown` | An entitled divorced spouse and an entitled child are on the record without a current-month care attestation (RS 00615.010/.201A.2) |
| `divorced_spouse_care_history` | Without current care, first-entitlement care is unknown or attested True, and continued exemption could change the settled auxiliary payable; different intermediate rates with identical payables are supported with a diagnostic note. Conversion and ARF history after care ends are outside this snapshot (202(k)(3)(A); RS 00615.201A.2; .010) |
| `delayed_credits_born_before_1917` | Delayed credits for births before 1917 (402(w)(6)(A)'s 1/12 of 1 percent) |
| `own_rib_history_before_1978` | A known own-RIB cohort before 1916, positive current PIA and positive reduction months: first entitlement could precede January 1978, and the historical reduction/PIA amounts needed by RS 00615.005C.2 are absent |
| `reduced_benefit_history_before_1978` | A reduced spouse or divorced spouse before cohort 1916, or widow(er), surviving divorced spouse or DWB before cohort 1928, whose missing pre-1978 reduction money history can change a payable, a maximum allocation or a savings-clause rate. The widow boundary includes possible earlier DWB and conversion at FRA (RS 00615.005C.2; .310A). Settled exceptions and the conservative DWB reading are detailed below |

`evaluate_family` and `count_family_outcomes` keep unsupported rows, whether
single records or households, in every denominator by reason and weight.
`weighted_record_total` and `weighted_mean_record_total` raise
`FamilyTargetBlocked` rather than drop them. Invalid inputs raise
`InvalidFamilyInput`. They are errors, not coverage gaps, and are never
absorbed as unsupported rows.

### Own-RIB reductions with pre-1978 entitlement history

RS 00615.005C.1 applies to "Initial Entitlement 1/78 or Later" and states:
"Subsequent higher PIAs or unreduced amounts (adjusted for family maximum
if necessary) are reduced by the original reduction factor (ORF)."
Its C.2 instead covers "Initial Entitlement Before 1/78" and computes
the new money amount of reduction from the new PIA, the current money
amount of reduction and the current PIA: `(NPIA or NUR) x CMAR / (CPIA or CUR)`.
The capture then directs: "The new money amount of reduction is subtracted
from the new PIA or the new unreduced rate to obtain the new monthly
benefit amount."

A cohort before 1916 could first receive RIB before January 1978. G's
inputs supply current PIA and reduction months after any ARF, rather than
first-entitlement date and the required money history. Even RF1 cannot
establish a late first entitlement. With a positive PIA and reduction,
these cohorts therefore raise `own_rib_history_before_1978` after all
input checks. A zero PIA or zero reduction does not require the missing
reduction amount. Cohorts from 1916 cannot first receive RIB before
January 1978; the existing current formula remains supported. If the
cohort is omitted, the scalar and family calculation retains its existing
current-formula domain; this does not validate an undated historical award.

The review's invented spouse has cohort 1912, own PIA $1,000 and RF1.
Previously G returned $994.40 without the historical inputs. It now
refuses, keeps the row and weight in every denominator, and blocks totals.
The captured text does not establish a replacement dollar amount, so no
historical payment is imputed. Changing the cohort to 1916, 1917 or 1935
keeps the supported $994.40 current-formula control. The new history tests
quote both instructions, exercise both cohort placements and all family
entry points, and compare the scalar calculation to an independent exact
fraction formula with zero tolerance. This implements a missing-input
coverage refusal and introduces no alternative statutory interpretation.

### Own-RIB widow support boundary

RS 00615.010 identifies "RIB After Reduced WIB (D then A) with date of birth
of 1/2/1928 or later" and directs: "Reduce the RIB in the usual manner
without regard to the WIB". RS 00615.020B specifies method D only when the
date of birth is "prior to 1/2/1928" for the stated widow-before-age-62
sequence. The statutory-source boundary is therefore January 2, 1928.

G retains cohort 1929 as its conservative implementation boundary to preserve
the previously validated support surface until sequence coverage is expanded
for cohort 1928. This is a known over-refusal, not a claim that the source
requires method D for cohort 1928. Birth years already denote SSA's
January 2-January 1 cohorts, so missing day-of-birth precision is not the
reason. No new statutory interpretation is selected.

The review's invented widow has survivor PIA and maximum of $1,000, own
RIB of $200 and no reductions or credits. Cohort 1928 remains refused as
`dual_entitlement_sequence`; changing only the cohort to 1929 admits own
$200.00 plus auxiliary $800.00 (whole dollars $200 and $800). The refusal
retains the 1928 row in every denominator instead of producing a zero
payment. `test_review_1928_widow_refusal_discloses_implementation_boundary`
pins an accurate diagnostic, the 1929 control pins the exact payments, and
`test_1928_source_boundary_is_quoted_from_captures` pins both source texts.

## Invariants (all executed as tests)

1. **The family maximum binds only where the statute says it does.** The
   worker's PIA plus every amount subject to the maximum never exceeds it.
   Only the worker's own delayed credits (RS 00615.695) and divorced
   beneficiaries (403(a)(3)(C)) fall outside. The worker's benefit never
   depends on the auxiliaries.
2. **Shares stay proportional.** Each share lies within one dime below OB x
   available / total OB. After a redistribution, the shares of beneficiaries
   who are not dually entitled are proportional to the pool and are never
   below their standard shares.
3. **Raising the PIA never lowers the family maximum.** This holds for the
   retirement/survivor formula and after COLAs, and for the disability maximum
   in both the PIA and the AIME. That maximum stays between the PIA and 150
   percent of the PIA.
4. **Adding an auxiliary who is not dually entitled never raises another
   beneficiary's rate, payment or total.** Adding a divorced beneficiary
   changes nothing for anyone else.
   - *Intended violation:* adding a dually entitled auxiliary can raise
     another's benefit under RS 00615.768E. The minimized counterexample is
     pinned as intended.
5. **Dual entitlement never leaves a person below their own benefit.** The
   auxiliary amount is never negative, and the person receives the larger of
   the own benefit and the age-adjusted auxiliary benefit.
6. **Unsupported configurations always raise**, including when injected
   anywhere in a valid family or shared between two records of a household,
   and the denominators always keep them. **Invalid inputs are never
   absorbed as refusals.** Delayed credits past 70, a record date after the
   payment month, or a duplicate id always raise `InvalidFamilyInput`, even
   with a refused beneficiary or record condition in the same family.
7. **Households are their records.** A household of unrelated records gives
   each record's own result, and its total is their sum.
8. **Results are deterministic and independent of beneficiary order.** Every
   amount is a dime multiple, and each whole-dollar payment is the floor of its
   amount.
9. **403(a)(5).** Along any month path that starts at entitlement:
   - an admitted month with anyone under the maximum is never below an
     earlier protected total, and never follows such a fall;
   - a refused month has someone under the maximum and a fall behind it;
   - a month with nobody under the maximum is always computed;
   - a path whose PIA never rises is never refused.
10. **Differentials.** The reduction fractions, `spousal_benefit` and
   `widow_benefit` in `ss/benefits.py` agree with G within their documented
   rounding. Its sealed legacy `delayed_credit` agrees with G through
   `min(48, window)` and keeps its 1935/60-month value of 0.24 by design.
   `ss/statutory_delayed_credit.py` agrees with G across the full statutory
   window for births from 1917, including months past 48. The scalar
   whole-window fraction differential uses PIA $2,400 to remove monetary
   rounding and has tolerance `1e-12`; G's arbitrary-dime-PIA monetary
   differential retains its one-dime tolerance. The sealed ledger's float path
   (`estimates.ledgers.floor_to_dime` over `early_reduction`) is never above
   G's exact amount, and never more than a dime below it.
11. **Delayed-credit windows.** For every cohort 1917-1960 on the RS
    00615.692E chart, the window is `840 - FRA` and the rate is the chart's.
    G accepts the whole window and rejects one month more.

12. **Widow cohort periods.** Every January 2-January 1 cohort fixes exactly
    one RS 00615.301B.2 period. Only 60, 62, ..., 84 are legal without a
    cohort. The primitives and both construction styles reject every other
    integer period, a conflicting cohort period or excess months before any
    refusal. Exact family payments equal the independent widow primitive
    with zero tolerance. Fix-round examples and Hypothesis tests execute
    every boundary cohort and the independent exact integer reference.
13. **Widow DRC protection.** Known RS 00615.712 protection and unknown
    history have distinct named refusals. Every refusal retains its row and
    weight and blocks totals; duplicate inputs raise first. Modern
    eligibility cannot hide known DIB by May 1978 or unknown prior DIB.
    First-ever DIB after May 1978 or an explicit no-protection attestation
    excludes the history refusal. Fix-round Hypothesis tests execute these
    rules, including the exact May/June boundary, in both construction
    styles.
14. **RIB-LIM scope.** A nonlimiting declaration has no effect on settled
    Parisi payments; equality is nonlimiting. Actually limiting cases retain
    refusals and denominators. Payment-review examples and Hypothesis
    properties execute equivalence, order independence and exact thresholds.
15. **Historical DIB scope.** Direct and built snapshots both refuse known
    initial DIB entitlement before July 1980. July is supported; impossible
    dates and duplicate members raise first. The payment-review differential
    and input-priority properties execute both entry styles.
16. **Registry tag truth.** Every binding/nonbinding tag matches at least one
    computed scenario in its example. Registry examples and Hypothesis
    tests reject false tags and preserve scenario order independence.
17. **Illustration compatibility.** All seven recorded G fields for every
    G-using household and month equal current G exactly. The unit
    compatibility module tests the finite set exhaustively and through
    Hypothesis; the artifact pin executes the proof before its one-file
    exclusion. This admits an invented-case regression only.
18. **Widow child-in-care minimum.** The widow's payable amount is the
    larger of its ordinary reduced amount and the mother/father comparison
    amount, with zero-tolerance differential, including settled dual
    offsets. A higher WIB is unchanged. Other beneficiaries keep their
    ordinary widow-family amounts. Subject totals remain within the
    maximum; an actual surviving-divorced payment remains outside it while
    its hypothetical 202(g) comparison is subject. Amounts remain
    nonnegative dimes, whole-dollar floors and
    sums remain exact, and results remain deterministic and independent of
    beneficiary order. Unknown care retains its row and weight and blocks
    aggregates; invalid named children raise before coverage refusals.
    Fix-round child-in-care examples and Hypothesis tests execute each rule.
19. **Divorced-spouse care.** Current care pays the unreduced spouse OB less
    the reduced own RIB, bounded between zero and OB. Changing auxiliary
    reduction months or own-RIB entitlement order does not change that
    payment. Adding the divorced spouse changes no worker or child amount,
    counts zero against the maximum, and preserves the subject-total cap.
    Amounts are exact dimes, record totals and individual whole-dollar
    floors add exactly, results are deterministic and independent of order.
    Unknown or protected first-entitlement care history that can change the
    auxiliary payable refuses; every row and weight remains in the denominator
    and both aggregates block. Malformed current-care references and history
    inputs raise before coverage refusals. The round-4 divorced-care examples
    and Hypothesis properties execute these rules, with exact differentials
    against the ordinary child-in-care spouse surface and both record
    construction styles.
    The round-5 property
    `test_property_care_history_refuses_exactly_when_payables_differ`
    additionally proves that refusal holds exactly when the ordinary and
    exempt payables differ. Equal payables remain supported even when
    intermediate rates differ; the note labels the ordinary intermediate
    rate as diagnostic and records the exempt alternative. Earlier notes
    survive that appended diagnostic, with every payment field unchanged;
    the round-6 `test_settled_care_history_appends_to_earlier_note` and
    `test_property_care_diagnostic_preserves_prior_note_and_payment`
    exercise this diagnostic invariant using an injected earlier note.
20. **One person, one cohort.** Supplying the cohort in the beneficiary
    field, the own-benefit field, the person's worker record, or any equal
    combination gives the same result or
    input error. Conflicting supplied cohorts raise before every refusal.
    That cohort bounds own-RIB and spouse reduction months at FRA minus
    744, and fixes the widow auxiliary period. Validation and computation
    use immutable normalized copies, preserving caller inputs. The direct,
    built, household, evaluated and guarded entry points agree exactly;
    invalid input leaves all monthly guards unchanged. The round-5
    `test_review_rf37_is_invalid_before_any_refusal`, RF36 controls and
    Hypothesis `test_property_cohort_placement_has_identical_outcome`,
    `test_property_conflicting_cohorts_are_input_errors` and
    `test_property_own_only_cohort_fixes_widow_auxiliary_period` execute
    these identities and bounds. Own-RIB calculation also equals the
    independent worker primitive with zero tolerance. The round-6
    `test_property_household_cohort_placement_and_order_are_equivalent`
    tests all seven nonempty placements across the three sources, record
    order, unchanged caller inputs and exact refusal weights. Its
    `test_property_household_conflicts_precede_refusals` checks conflicting
    years before refusal and before either monthly guard advances. The
    round-6 RF36 control also equals explicitly annotated standalone
    records with zero tolerance. Auxiliary-only repeated people obey the
    same conflict rule under
    `test_property_auxiliary_only_cohort_conflicts_precede_record_refusals`;
    a shared spouse's RF36 preserves the multiple-record refusal and RF37
    is invalid in
    `test_auxiliary_only_shared_cohort_precedes_multiple_record_refusal`.
    This invariant holds independently of own-benefit entitlement and
    record kind. The round-7
    `test_review_unclaimed_worker_cohort_makes_rf37_invalid` and
    `test_unclaimed_worker_cohort_conflict_precedes_gpo` reject the
    unclaimed worker's RF37 and conflicting metadata before GPO or guard
    advancement. Its RF36 control pays $375.00 auxiliary and $1,375.00
    household total, or retains the GPO refusal with weight 7/3.
    `test_property_unclaimed_cohort_validation_is_order_independent`
    checks cohort propagation, exact equality with explicitly supplied
    cohorts, immutable inputs, record order and unchanged guards on errors.
    `test_property_unclaimed_builder_and_direct_cohorts_agree` compares
    both construction styles exactly;
    `test_property_record_builder_preserves_cohort_without_rib` covers
    every record kind independently of entitlement.
    `test_property_record_and_own_cohorts_reconcile_immutably` checks all
    metadata placements and conflicting years, and
    `test_property_unclaimed_cohort_conflicts_precede_refusals` exercises
    conflict priority across construction styles and record orders.
21. **Historical own-RIB scope.** Positive reductions of a positive own
    PIA for known cohorts before 1916 always refuse with
    `own_rib_history_before_1978`; each row and weight remains in its
    denominator and aggregate totals block. Invalid reduction inputs
    raise first and leave monthly guards unchanged. A zero PIA or zero
    reduction stays supported, and cohorts from 1916 match the independent
    exact current formula with zero tolerance.
    `test_property_historical_reduction_refusal_preserves_denominators`
    and `test_property_1978_boundary_preserves_post_1977_formula` execute
    the coverage/denominator and arithmetic properties.
    `test_history_refusal_follows_all_family_input_errors` and the
    unreduced/zero-PIA controls execute their boundary cases. The former
    varies old cohorts and impossible auxiliary reduction months through
    Hypothesis while retaining the explicit 1912/RF37 control;
    `test_property_zero_pia_or_zero_reduction_needs_no_history` executes
    both supported exceptions across cohorts 1900-1915.

22. **Historical auxiliary scope.** Missing reduction-money history refuses
    for pre-1978-capable spouse, divorced-spouse and survivor cohorts when
    conservative bounds leave the payable, maximum allocation or protected
    pre-offset rate unsettled. Zero reductions and settled exceptions remain
    supported; the automatic DWB reduction has its explicit conservative
    interpretation below. `test_property_history_refusal_exactly_tracks_role_cohort_and_amount`
    executes every auxiliary role/cohort and preserves refusal denominators.
    `test_property_invalid_family_member_precedes_every_history_refusal`
    checks error priority and guards. The properties
    `test_property_zero_spousal_excess_survives_parisi_redistribution`,
    `test_property_current_divorced_care_exemption_settles_historical_rate`
    and `test_property_zero_rib_lim_settles_positive_outside_maximum_history`
    pin settled exceptions, using exact comparisons. The
    `test_settled_subject_payable_does_not_fabricate_savings_clause_rate`
    regression rejects hidden variation in a subject's protected rate.

23. **Schema-declared input validation precedes coverage.** Corrupting one public
    input field of a valid invented family with a wrong type or an invalid
    value raises `InvalidFamilyInput` at every applicable entry point.
    This includes exact enum classes, booleans distinct from integers,
    monetary values, dates, conditions, household metadata and public
    guard inputs.
    No outcome is returned, no row or weight enters a refusal denominator,
    caller inputs remain unchanged and every monthly guard retains its
    state. `test_review_malformed_inputs_precede_refusal_and_guard` pins
    the executed counterexamples.
    `test_malformed_catalog_covers_every_public_input_dataclass_field`
    checks the corruption catalog against dataclass fields, and
    `test_malformed_field_never_counts_or_advances_any_entry` applies its
    corruptions to Hypothesis-generated families across the direct,
    built, household, evaluated and guarded routes.
    `test_malformed_property_starts_from_supported_families` checks the
    valid seeds.
    `test_property_malformed_outcomes_never_compute_count_or_advance`
    checks outcome keys, weights and callables before a closure runs or a
    guard advances. Valid coverage refusals continue to retain their rows
    and weights as required by invariant 6.
24. **Refusal precedence is shared across entry points.** On identical
    valid inputs, direct and built snapshots and household entry points
    select the same refusal reason, including pre-1983 eligibility
    combined with record conditions. Record refusals use eligibility
    before 1983 first, then conditions in alphabetical value order, then
    historical DIB entitlement. Record order remains canonical at the
    household level. `test_review_pre_1983_refusal_precedence_matches_every_entry`,
    `test_property_all_single_record_entry_points_have_identical_outcomes`
    and `test_property_multi_record_entry_points_have_identical_outcomes`
    execute the regression and cross-entry differential with zero
    tolerance for reason codes and supported payment fields.

25. **Public object and helper closure.** Every public dataclass field and
    exported function argument is classified against `__all__`, dataclass
    fields and callable signatures. A single malformed type, wrong enum
    class, non-finite value or out-of-domain value raises
    `InvalidFamilyInput` before producing an object or outcome, contributing
    a row or weight, or changing a monthly guard. Public consumers also
    revalidate caller-supplied results and refusals. The Hypothesis tests
    `test_every_public_constructor_field_rejects_corruption` and
    `test_every_public_argument_rejects_corruption_before_output` execute
    the corruption catalog; `test_public_api_has_no_unclassified_name_field_or_argument`
    prevents additions escaping it. `test_public_argument_properties_start_from_valid_calls`
    verifies that every function's uncorrupted seeds remain valid.
    `test_parameter_field_corruption_preserves_guard_and_denominator`
    extends the property to supplied NAWI and delayed-credit series entries.
    `test_result_and_denominator_total_identities_reject_positive_corruption`
    checks result and denominator identities;
    `test_result_mappings_are_immutable_snapshots` checks mapping isolation.
    `test_guard_revalidates_entire_result_before_any_state_change` and
    `test_guard_revalidates_refusal_before_skipping` cover altered nested
    values, and `test_consumers_validate_all_rows_before_coverage` checks
    that an earlier valid refusal cannot mask a later malformed row.
26. **Citation containment.** Each registry citation resolves to headings
    present in its capture, and every quoted figure occurs within those
    section boundaries. `test_registry_cited_section_contains_every_published_figure`
    executes all 29 entries, `test_registry_unknown_sections_are_rejected`
    is the Hypothesis malformed-citation property, and
    `test_registry_other_parisi_example_figures_are_rejected` prevents a
    valid but wrong section from borrowing figures elsewhere in the capture.

## Worked examples reproduced exactly

| Source | Case |
| --- | --- |
| RS 00615.756 | $138.00 and $103.50 each, with 7 children (FMAX $862.60); the windexed widow and child, $260.70 / $189.20 |
| RS 00615.710 | Widow DRCs share the maximum: $404.20 / $295.70 |
| RS 00615.682 | $101.90 each; then the surviving divorced spouse at $145.70, outside the maximum, and children capped at $152.90 |
| RS 00615.768 | Examples 1 and 2 (the Parisi rule): $125.00 each; $30 / $270 |
| RS 00615.320 | RIB-LIM $350, with the $309.20 floor |
| RS 00615.340 | Example a: 64 reduction months, 71.5 percent raised to 75 percent for January-June 2005, then 71.5 percent from July. Example b: 16 months, about 92.9 percent unchanged. On the explicitly invented $1,000 scale these are $750.00/$715.00 and $928.70 (whole dollars $750/$715/$928) |
| RS 00615.240 | Spouse then RIB (method B): $450.00 spouse, $200.00 RIB, $250.00 paid as a spouse |
| RS 00615.694 | Spouse payment $290 after delayed credits on the own RIB |
| RS 00615.005, .101, .201, .301, .692 | $780.50 (not $780.40); every chart fraction; $819.60; $1,175; every RS 00615.692E cohort's maximum delayed-credit months |
| RS 00615.736 | Unrounded $659.02 / $647.89 / $625.23 / $759.238, and the pre-1982 round-up that is refused |
| RS 00605.900, .910 | All bend points and chart constants, 1979-2026 |
| OACT family maximum | 2026 bend points from NAWI(2024) |
| SSB 75(3) | Tables 1, 2, A-1, A-2 (dollar presentation rounding); A-2 also as a two-record household ($1,900) |

## Findings recorded along the way

- **Source erratum.** RS 00605.910 prints `899.52` for 1981's third constant.
  The statute gives `889.52`, and RS 00615.736's 1981 example agrees with the
  statute. The test pins both figures.
- **The sealed ledger's float path lands a dime low about 3.5 percent of the
  time.** `ss.benefits.early_reduction` uses policyengine-us's decimals
  `0.00555556` and `0.00416667`. `estimates.ledgers.floor_to_dime` applied to
  that product can therefore only land low. Over every PIA from $0.10 to
  $557.20 by dime and 1-60 reduction months (334,320 cells), it lands a dime
  low in 11,572 cells (3.46 percent) and never high. A test pins these
  counts. Over PIAs to $4,500.00 (2,700,000 cells) the count is 94,530
  (3.50 percent); that wider figure comes from a one-off script, not a test.
  POMS's own example is low in that wider one-off count, outside the
  334,320-cell ledger ($802.80 over 5 months gives $780.40, not $780.50).
  G uses exact fractions and pins this example. The
  sealed ledger is not edited here.
- **No Axiom differential yet.** rulespec-us at `83abd9ece` (origin/main,
  2026-09-29) has no `us/statutes/42/403` encoding. Its 402(a)/(q)/(w) and
  415(a)/(b)/(i) encodings do not cover the maximum. Per d515 the
  differential waits for a pinned rule and stays diagnostic when it comes.
- **Capture integrity.** Three POMS captures (RS 00605.900, RS 00615.756 and
  .768) were re-fetched on 2026-09-29 and matched their manifest SHA-256
  byte for byte. Every Bulletin figure the tests quote was found on the live
  page the same day.
- **Review round 1 (g-r1).** The review found two medium issues. First,
  legal delayed-credit months were refused under a 48-month cap, and
  impossible ones were accepted. Second, the 403(a)(5) detector compared
  only consecutive months. It also found four low issues:
  - the pre-1917 credit rate;
  - a silent default for the spouse entitlement order;
  - a public single-record entry point;
  - no check of record dates against the payment month.

  All six are fixed above, each pinned by a test written to fail first.
  RS 00615.801 and RS 00630.400 were captured on 2026-09-30, and 402(w)(2)
  and (w)(6) were added to the LII excerpts from a body that matched the
  pinned SHA-256.
- **Statutory delayed-credit convention #494 (2026-10-11).**
  `ss/statutory_delayed_credit.py` credits every month from FRA to the
  month before 70, beside the unchanged sealed oracle. A 1935 birth
  entitled at 70 agrees with G at 30 percent of PIA under `STATUTORY` and
  retains 24 percent under `LEGACY_48_MONTH_CAP`. The statutory table and
  full-window differentials are described in `track_b_494_delayed_credit.md`.
  The erratum audits registered-result reachability; those results stand
  under their registered legacy convention. A later registered rerun must
  select `DelayedCreditWindow.STATUTORY` explicitly and state that choice.

## Not in scope

- RET deductions and their ordering against the maximum (403(a)(4) first
  sentence) are R2's.
- ARF and recomputation are R3's.
- Divorced-spouse conversion and ARF history after care ends are outside
  this snapshot. Unknown or protected first-entitlement care history that
  changes the auxiliary payable raises `divorced_spouse_care_history`
  (RS 00615.201A.2; .010).
- Monthly timing and event journals are I's. For 403(a)(5), I must feed
  every month of each record, from its first month of entitlement, to one
  `SavingsClauseGuard`, and keep the guard's refusals in its denominators.
- No population, behavioral or forecast claim is admitted.
- `engine/loop.py`, `engine/steps.py`, `gates.yaml` and committed `runs/` are
  untouched.


## Conformance review of October 11, 2026

Input checks precede coverage refusals for both direct `RecordState` inputs
and `WorkerRecord` inputs built inside `evaluate_family`. `record_state`
carries a deferred refusal; a pre-1983 maximum sentinel is never payable.
402(q)(6) and RS 00615.010 bound worker and spouse reductions at FRA minus
744 months when the cohort is given in either beneficiary birth-year field.
RS 00615.692E bounds pre-1917 credits
at year-only maxima of 84 months through 1912, 72 for 1913, and 60 for
1914-1916 (the earlier bands depend on birth month);
legal credits remain refused because the bundle lacks their rate.

The own-benefit birth year must match the beneficiary's when both are
provided. When one is omitted, the other supplies the person's effective
cohort for validation and calculation. Every birth-year input denotes
SSA's January 2 through January 1
cohort; a January 1 birth uses the previous cohort year. RS 00615.301B.2
therefore fixes a widow's reduction period for every cohort, including
boundary cohorts. A supplied period must match it and reduction months
cannot exceed it. Under 403(a)(2)(D), retirement eligibility cannot be
later than birth year plus 62, but an earlier DIB eligibility year is kept.
These bounds and input-before-refusal order extend invariants 6 and 11.

The final denominator audit executed another minimized instance of
invariant 6: a closure constructing an own DIB with one prior-RIB reduction
month and duplicate child ids returned `dib_after_reduced_rib`. OwnBenefit
now carries that valid unsupported configuration without refusing in its
constructor; the refusal is raised by `own_monthly_benefit` or the family
coverage stage after every input check (402(q)(2)). The standalone primitive
also validates impossible reduction months before refusing. The new
own-input-order tests execute both construction styles and Hypothesis
duplicate, wrong-role and invalid reduction-field cases. Valid reduced-DIB
configurations retain the same refusal and denominator.

`household_month_outcome` validates every input and guard before advancing
any guard. It advances every record for the month and returns one household
outcome, attaching the record id to a record refusal. This extends
invariants 7-9 to the monthly assembly entry point. The guard does not
compute the saving-clause raise. A child leaving in June after a December
COLA can trigger refusal, and every later governed month remains refused,
including an aged-widow month in the next year. The review's executed
survivor case begins with a 2020 record, PIA $1,500 and maximum $2,584.20,
a mother and two children. A December 2025 COLA raises the total to
$2,648.70; one child leaves in June 2026 and the total falls to $2,306.20.
`test_review_child_departure_six_months_after_cola_refuses_later_widow`
executes the entire path, including a refused 2027 widow month.


## Dual entitlement and deduction before reduction

GN 02603.045 applies the new rule to benefits payable from October 1999
(the earlier First Circuit cases remain refused). GN 02603.050C defines
PTAP as the family maximum less the life-case PIA, auxiliary age reduction
amounts for deductees, and their partial payable amounts. Other deductions
are R2's. Its non-deductee formula is OB times PTAP divided by TOTOB less
the deductees' OBs, capped at OB and dime-floored. GN 02603.050A.2 excludes
a dual rate reduced to zero; all-dual families retain the ordinary maximum.
`maximum_redistribution_rates` accepts payable amounts and separate age or
other deduction amounts so R2 can extend deduction handling without
rewriting distribution. GN 02603.050D's temporary cases require R2 to
select each eligible household's denominator and supply its OB mapping
separately. This helper computes rates, not work deductions.

GN 02603.060 examples A.5, A.8, A.9 and B.2 are reproduced. A.5 pays
children $125 each and spouse $0 plus own $100. A.8 pays children $125 each
and spouse $0 plus reduced own $80. A.9 pays the aged spouse $112.50, one
child $150, and a dual child $0 plus own DIB $200. B.2 pays spouse $2.40
plus own RIB $64 and children $123.30 each: PTAP is $750 minus $500 minus
$0.90 minus $2.40, or $246.70. The own-RIB $16 age reduction is not removed
from this pool. Both C examples involve work deductions and belong to R2.

Invariants 1, 2, 5 and 8 extend to own RIB age reduction. The pure PTAP
helper is deterministic and independent of mapping order, returns only
non-deductee ids, caps rates at OB, floors to dimes, and allocates at most
the nonnegative pool. Separate supplied deductions reduce that pool
monotonically. Its independent exact formula property provides a
differential with zero tolerance. Own delayed credits and an actually
limiting RIB-LIM remain
`parisi_redistribution_ambiguous`: no captured example settles their
interaction with the PTAP age-reduction and partial-payable terms.


### Zero reached after auxiliary age reduction

This reading needs Max's judgment. GN 02603.045 says the counted amount is
"before any applicable reduction for age". GN 02603.050C requires the
"Age reduction amount for all workers or deductees". GN 02603.050A.2
instead says "If dual entitlement reduces a beneficiary's rate to $0.00
(technically entitled)" to disregard that beneficiary. A method-B spouse
with PIA $500, maximum $750, own RIB $64 and 36 auxiliary reduction months
has standard rate $83.30, age-adjusted $62.40, and zero auxiliary payable.
Disregarding the spouse pays children $125 each; retaining the $20.90 age
term pays $114.50 each, a $21 record-total difference. A reading of the
before-age text alone counts $83.30 minus $64, or $19.30, paying children
$115.30 each and a record total of $730.60. G refuses this
case as `parisi_redistribution_ambiguous`, rather than selecting the higher
payment. Zero before auxiliary age reduction is supported, including A.5
and A.8. The alternatives and the refusal are executed by the Parisi tests.

Ruling d1418 (2026-10-12): keep the current defaults; reopen any one when a
population target needs it.


## Disabled widow(er) benefits

402(e)(1)(B)(ii) and (f)(1)(B)(ii) provide disabled widow(er) entitlement
at 50-59. The caller attests that entitlement; G does not adjudicate medical
or insured status. RS 00615.310B.1 says "DWB are reduced by 28.5 percent.
No additional reduction applies for the period before age 60." B.3
recalculates earlier entitlements effective January 1984 without the pre-60
reduction. G therefore supports payment months from January 1984 and refuses
prior months as `disabled_widow_before_1984`.

DWB OBs use the widow basis, share the family maximum, then take a fixed
28.5 percent reduction whose amount rounds up to a dime (402(q)(8);
RS 00615.301). The RIB-LIM then applies under 402(e)(2)(D) and RS
00615.320's general widow(er) rule. Reduction-month inputs are invalid for
this fixed initial reduction; later ARF adjustments belong to R3.
RS 00615.315 discusses election between WIB and DWB, not sequencing of an
own RIB or DIB. Both own-benefit combinations remain refused as
`dual_entitlement_sequence`.

Captured DWB sources contain rules without monetary worked examples.
Invented hand references use a $1,000 OB: reduction $285 and payable $715.
A $1,000.10 OB has reduction $285.10 (up from $285.0285) and payable $715.
Invariants: the reduction is exactly ceil-dime of 28.5 percent of the
post-maximum rate, payments are nonnegative dime amounts, are monotone in
the rate, and equal the existing widow helper at a full reduction period
(zero-tolerance differential). Family-maximum bounds and beneficiary-order
independence continue to hold. The DWB example and Hypothesis tests execute
these rules and the January 1984 boundary.


## Social Security Fairness Act

Pub. L. 118-273 was enacted January 5, 2025. The captured GN 02608.100
and RS 00605.360 bodies state that it eliminates GPO and WEP "for benefits
payable for months after December 2023" and that regular payments begin
with benefits due for January 2024, paid in February 2024. This is the
benefit-month boundary, not the enactment month or check month. A declared
GPO condition remains `government_pension_offset` through December 2023;
from January 2024 it has no effect on G's computed benefit.

G takes a PIA; it does not compute WEP. Before January 2024 the caller is
responsible for the WEP-affected PIA and associated maximum (RS
00605.360C.3). From January 2024 supply the regular-formula eligibility-year
PIA and its COLAs to rebuild the regular maximum. Keeping a pre-repeal
WEP PIA as input would not implement the repeal. The captures have 2025
transmittals despite older displayed page dates; the pinned body supplies
the repeal text. Invariants: exact equality between flagged and unflagged
post-repeal families and households; refusal retention before repeal; and
input validation preceding either payment-month branch. SSFA example and
Hypothesis tests execute the December 2023 / January 2024 boundary.

## Independently entitled divorced spouses and parents

From January 1985, `WORKER_NOT_ENTITLED` identifies a living, insured,
eligible worker who has not claimed. The caller attests two continuous
years of divorce for each beneficiary (202(b)(4)(A), (c)(4)(A); RS
00202.005 and .100). Only divorced spouses are admitted on this retirement
record. Their OB is half the eligibility-year PIA after applicable COLAs,
with the ordinary spouse age reduction and dual-entitlement methods. They
are outside the maximum, and no worker payment is added. The public
`WorkerRecord` and `RecordState` accept this form; household checks distinguish
an unclaimed living worker from a deceased worker. A WEP-affected worker
record, declared with `WINDFALL_ELIMINATION_PROVISION`, is refused for IEDS
before January 2024 (RS 00202.100's WEP note). That flag has no effect from
January 2024 under Pub. L. 118-273. Ordinary records still take the caller's
correct PIA; this layer does not calculate WEP.

Parents on survivor records use 82.5 percent for one entitled parent and
75 percent each for two, floored to a dime (202(h)(2); RS 00209.015). The
maximum applies before 202(k)(3)(A)'s own-benefit offset. There is no age
reduction. A parent's own RIB must be less than the parent's OB to establish
entitlement (RS 00209.001). This compares the actual reduced or credited
own RIB and the dime-rounded OB, rather than the own PIA. An own-DIB parent
remains technically entitled even if no parent benefit is payable (RS
00209.015); that parent still counts for the two-parent rate. More than two
declared parents is refused as `parent_benefit`: the captured one/two-parent
rules do not settle that configuration.

Needs Max's judgment: the parent entitlement count can be circular. RS
00209.001 requires "not be entitled to retirement insurance benefit (RIB)
equal to or exceeding
the amount of the parent's original benefit (One parent = 82 1/2%; Two parents
= 75%);". RS 00209.015 distinguishes "2. One parent entitled" from
"3. Two parents entitled". For PIA $1,000 and maximum $1,750, two potential
parents, one with own RIB $780, qualify together at the one-parent OB of
$825 but that first parent's RIB exceeds the two-parent OB of $750. Counting
two first excludes that parent and pays the other $825; testing eligibility
at $825 first would count two and pay the other $750 (a $75 difference),
while paying no auxiliary to the $780 own-RIB parent. Neither fixed order
is silently selected: `parent_benefit` refuses the interval between the two
dime-rounded OBs when both parents are potential entitlements.

`test_parent_entitlement_count_counterfactual_changes_payment_by_75`
executes both readings with a test-only exact helper. Counting two first
tests entitlement at $750, excludes the $780-own-RIB parent, and gives the
other parent's candidate payment $825. Rechecking entitlement at $825
would count two. Testing entitlement at $825 first counts two, changes the
other parent's candidate payment to $750, and then excludes the first
parent when entitlement is rechecked at $750. Both candidates pay that
first parent no auxiliary, and the other parent's candidates differ by
$75. The public result remains the `parent_benefit` refusal. The Hypothesis
test `test_parent_count_counterfactual_orders_cycle_across_the_refused_band`
executes the same count reversal and the exact difference between the two
dime-rounded OBs throughout the refused interval. These reversals are an
intended diagnostic inconsistency of the two one-pass readings, not a
supported payment or a bug in the public refusal.

Ruling d1418 (2026-10-12): keep the current defaults; reopen any one when a
population target needs it.

Invented hand references (the captures publish rules without monetary
worked examples for these classes): PIA $1,000 pays a solo parent $825 or
two parents $750 each. An own RIB of $1,000 reduced for 36 months is $800
and leaves a solo-parent auxiliary of $25. Two parents and a child with
maximum $1,500 and one parent's own DIB $600 pay $0/$750/$750; own DIB $100
pays $400/$550/$550 after redistribution. IEDS OB $500 reduces to $375
for 36 months. With method C, own PIA $200 reduced to $160 leaves the
$300 spouse excess reduced to $225; the own record is counted once when
present in the household.

Additional executed invariants are: parent rates follow the entitled count;
own DIB remains technical while disqualifying own RIB does not count;
parent allocations retain exact dime arithmetic, maximum bounds and order
independence; adding a subject child cannot increase an existing payment;
IEDS has no worker payment, ignores the maximum, and adding another divorced
spouse leaves existing payments unchanged; dual offsets remain nonnegative
and exact; January 1985 and January 2024 boundaries are deterministic;
refusals remain in denominators and every invalid family is checked first.
The new parent/IEDS tests execute examples and Hypothesis checks beside them.

## Registry, coverage and invented denominators

`tests/data/track_b/gross_benefit_examples.yaml` is the single statutory
worked-example registry. Its 29 entries reproduce 216 figures quoted from
the manifest's captures and 65 separately labelled derived rates or
whole-dollar floors. Each figure links an output path, exact expected value
and verbatim capture literal. The .910 erratum retains published $899.52
beside the formula's $889.52. Bulletin presentation rounding is separate:
Table 1's displayed $659 is an exact $658.50 rate and a statutory $658
whole-dollar payment, with whole-dollar family total $1,974. These derived
figures are not represented as printed source figures.

The tag vocabulary enumerates record kind, every role, reductions, credits,
dual method, binding/disability maxima, redistribution, outside-maximum
roles, RIB-LIM, COLA, DWB, parent, IEDS, SSFA and widow child-in-care
classes. All 43 supported classes have a registered example or one of 17
explicit invented-only explanations with test references. The coverage
test derives kind and role classes from G's enums; a missing supported
class, figure or source literal fails. Hypothesis tests execute
completeness, class loss, determinism and scenario order independence.

`scripts/track_b_g_conformance_report.py` writes the canonical JSON report
under this design directory. The exhaustive declared product is three
record kinds, all 55 role multisets of sizes zero through two, eight dual
modes, two reduction flags, three payment eras, fifteen single-condition
choices and three current child-in-care inputs (`None`, `False` and the first
entitled child's id). Focal flags apply to the first beneficiary in Role
enum order; empty multisets with a beneficiary flag are invalid. Fixed
invented money, cohort and snapshot assumptions are stated in the artifact.
Conditions are none or one declared record/beneficiary flag; combinations
beyond that finite axis and larger families are not claimed as enumerated.
The care input
applies to every widow(er) and divorced-spouse role in the cell; divorced
spouses explicitly attest False for first-entitlement care. A named-child cell without a
child is invalid, and unknown care with an entitled child refuses. Cells
without these roles still retain all three care choices in the denominator.

There are 356,400 cells: 8,831 supported, 60,775 refused and 286,794 invalid.
All cells stay in the denominator. Twenty-eight named invented witnesses form
a separate denominator, one executed refusal for every retained reason,
including historical, multi-record and protected-path cases absent from the
lattice. The `own_rib_history_before_1978` witness retains the cohort-1912,
own-PIA-$1,000, RF1 case; that reason is absent from the lattice's fixed
1946 cohort. The `reduced_benefit_history_before_1978` witness adds the
cohort-1912 spouse with no own benefit and RF1; its lattice count is also
zero. Statutory registry counts are separate again. These are invented
configuration counts, with no population weights or population claim.

Report invariants are unique/exhaustive declared cells, supported/refused/
invalid conservation, reason and era conservation, deterministic/order
independent classification, invalid-before-refusal order, separate
denominators and canonical byte equality on regeneration. Each is executed
by example and Hypothesis checks in the conformance-report tests. The
original review's ten deliberate mutations failed and were restored; the
commands and failing tests are listed in the pull request (#530). Fix-round
mutation evidence is recorded separately in `scratch/review`.


## Fix round of October 12, 2026

RS 00615.320A.3 applies RIB-LIM only when the widow's rate after maximum
and age reduction exceeds both 82.5 percent of the death PIA and the RIB
or DIB the deceased would receive. A declared limit that cannot change
this rate does not trigger the Parisi refusal. The review's invented
PIA $1,000, maximum $1,750, old RIB $100, widow own RIB $200 case has
standard widow $700 below the $825 threshold; redistribution pays widow
$500 and children $625 each, exactly as without the irrelevant limit.
Equality and a case where age reduction makes the limit irrelevant are
separately pinned. Actually limiting redistribution remains refused.
The direct historical-DIB guard now follows the same coverage rule as the
builder (RS 00615.740B.2). RS 00202.100 requires the WEP PIA for pre-2024
IEDS; G's comment now describes that calculation as unimplemented.

### Widow DRC saving clause

RS 00615.712 protects beneficiaries entitled for May 1978 against a future
reduction because a widow(er) receives the deceased's delayed credits.
The capture says, "The only criterion for this to apply is entitlement for
the specific month of 5/78." Entitlement in another month does not establish
or exclude protection. Benefit-rate preservation is not implemented;
`WIDOW_DRC_SAVINGS_CLAUSE` marks a protected beneficiary and refuses the
family as `widow_drc_savings_clause`. A direct `RecordState` can declare
that protection with `widow_drc_savings_clause=True`.

When a widow(er) subject to the maximum has an OB that may include
deceased-worker delayed credits and another beneficiary is subject to the
maximum, both direct and built snapshots need
`widow_drc_savings_clause=False` or complete first-ever DIB history that
excludes May 1978 protection. The default `None` refuses as
`widow_drc_savings_clause_history_unknown`. `first_dib_entitlement=None`
means unknown history; it does not attest no DIB. Modern current
eligibility does not exclude May 1978 protection: RS 00615.736B.2b permits
a new eligibility year after an earlier DIB period ended. A known
first-ever DIB entitlement after May 1978 excludes the protection; one on
or before that month does not. The larger-OB input also represents
windexing without a separate cause field, so an explicit exclusion is
needed to distinguish that case when the history cannot settle it. Existing
published snapshots attest exclusions from their captured facts: no DRC
widow, windexing, or first survivor entitlement in March 2000. Invented
snapshots explicitly assume no protected May 1978 beneficiary. All family
input checks precede either new refusal.

The published .712 case has March 2000 entitlement, PIA $400, ordinary
maximum $700, a child continuously entitled since March 1978, and widow
DRCs $10. Widow OB $410 plus child OB $300 totals $710. Ordinary
apportionment gives widow $404.20 and child $295.70. Protection keeps the
child at $300, so the master record's savings maximum is $704.20 and the
whole-dollar total is $704. The test independently reproduces every step
and checks every figure against the capture. G refuses the family with
either $700 or the master-record $704.20 maximum. The prior code paid
$406.60/$297.50 using that latter maximum (whole-dollar total $703).
This is an omitted settled rule, not a competing statutory reading.

### Widow(er) with an entitled child in care

RS 00615.340 states, "Any month a person receiving a reduced widow(er)
benefit has an entitled child-in-care they cannot receive less than the
amount a mother and father would receive. The benefit amount is raised
for all months the child is in care." RS 00615.010 repeats that minimum.
The policy applies to benefits payable from January 1973. G's pre-1983
payment scope already refuses every earlier month; it does not extend the
floor to historical months outside that scope.

`child_in_care` names one entitled child on the same worker record for the
payment month. `False` explicitly attests no entitled child in care;
`None` is unknown. Invalid ids, another record's child, non-child ids and
non-entitled children are input errors before any coverage refusal. When
an entitled widow(er) and an entitled child are present but care is unknown,
`widow_child_in_care_unknown` refuses and preserves the invented row and
its weight. The generic reduced-WIB rule covers disabled widow(er)s too.
RS 00615.340 expressly includes a surviving divorced spouse who elected
reduced benefits. The hypothetical mother/father benefit under 202(g)
remains subject to the maximum: 403(a)(3)(C) exempts divorced-spouse
benefits under 202(b)/(c) and surviving-divorced-spouse benefits under
202(e)/(f), and does not name 202(g). The actual surviving-divorced payment
stays outside the maximum and does not lower anyone else's share.

The comparison replaces the caregiver with a mother/father entitlement,
whose OB is 75 percent of the death PIA (202(g)(2)), applies the family
maximum and settled Parisi rules as that entitlement would be paid, and
keeps any own-benefit offset. The widow gets whichever amount is larger.
With PIA $1,000 and maximum $1,750, a 1935 widow reduced for 60 months and
one child receives $750 with the child in care, rather than $715 without;
the child receives $750 in either case and the caring total is $1,500.
With two children and a binding maximum, the mother/father share is
$583.30, rather than the unadjusted $750 OB; the ordinary widow rate is
$500.50 and each child keeps its ordinary widow-family $525 share. The
caring total is $1,633.30. This pins reduction after the maximum without
reallocating the children's ordinary widow shares.

For a surviving divorced spouse and two children with the same $1,000 PIA
and $1,750 maximum, the hypothetical mother receives $583.30. The ordinary
divorced widow receives $715, so current care leaves that payment at $715;
each child receives $750, total $2,215. RS 00615.682 supplies a published
control through this same path: PIA $203.90, maximum $305.90, hypothetical
mother $101.90, actual divorced widow $145.70 after 60 reduction months,
and children $152.90 each. The record total is $451.50, and individual
215(g) floors sum to $449. Every published figure is checked verbatim in
the manifest-listed capture. The minimized invented dime case has PIA
$0.40 and maximum $0.60: the widow receives $0.20 rather than $0.30.
The minimized whole-dollar case has PIA $2.70 and maximum $4.00: the widow
receives $1.90, floored to $1, rather than $2.00, floored to $2.

Example a in RS 00615.340 publishes 64 reduction months and 71.5 percent
WIB, raised to 75 percent for January-June 2005 while an entitled child
is in care, then returned to 71.5 percent in July. Example b publishes
16 reduction months and about 92.9 percent, unchanged because it exceeds
75 percent. The registry's invented $1,000 PIA gives exact rates $715.00,
$750.00 and $928.70, and floors each monthly payment under 215(g). The
source's "about 92.9%" is presentation rounding of 92.87 percent after
the dime reduction; both values are retained separately, without an
erratum or adjusted statutory calculation.

RS 00615.340 states, "At FRA attainment the widow(er) is granted an ARF
to remove all months the increase was applied". G computes the current
floor only. R3's certified mother/father-rate months already cover these
ARF crediting months; G does not reduce the supplied reduction-month count
or perform the FRA adjustment. A higher WIB is unchanged and earns no ARF
credit from this rule. The odd-period, care-minimum and unknown-prior-DIB
findings correct omitted settled rules and inputs. They introduce no new
competing statutory reading; the prior Needs Max's judgment items remain.

### Artifact compatibility and registry truth

The committed depletion-cut illustration retains its original provenance
commit and recorded `track-b-g-v1` version. The unit compatibility test
reconstructs each G-using household's worker, spouse and COLA inputs for
every recorded month and requires exact equality of PIA, maximum, binding
flag, worker payment, spouse OB, spouse payable and spouse payment. It
uses the published-NAWI unit bundle. The provenance gate executes this
proof before excluding exactly `gross_benefits.py` from its source pin.
No artifact bytes or recorded provenance are changed.

The `ssb-table-a1` registry tag is `maximum:binding`: its $1,800 maximum
leaves $300 for each child after the $1,200 worker. Every example's maximum
tag is now checked against its computed scenarios. The conformance JSON
is regenerated with this tag and the named .712 refusals, including the
expanded condition axis and both new refusal witnesses. These remain
invented configuration counts without population weights or claims.

### Non-finite parameter bundles

The 402(q), 402(b)-(f) and 402(e)(2)(D) bundle cross-check rejects NaN and
both infinities with the same `InvalidFamilyInput` (also a `ValueError`) as a finite statutory-rate
mismatch. The eight checked values are both worker monthly reduction rates,
both spouse monthly reduction rates, the survivor reduction floor, the
RIB-LIM PIA share, the spouse PIA share and the survivor PIA share. The
existing absolute tolerance remains `1e-7`; accepted decimal encodings are
still replaced by the exact statutory fractions (RS 00615.005B).

The reviewed-head comparison admitted NaN because its absolute difference
never exceeded the tolerance. Household paths could also refuse combined
records before checking any rate, even a finite mismatch. Each record's
input-validation pass now checks the bundle before household coverage
decisions, including `household_month_outcome`, so invalid parameters cannot
become coverage outcomes or advance a monthly guard. `evaluate_family`
continues to catch coverage refusals only.

The numeric audit found another minimized counterexample: an infinite FRA,
PIA $1,000, cohort 1960, zero reduction months and zero delayed-credit months
returned $1,000; the credit-window helper returned non-finite windows for
all three non-finite values. All three FRA lookups now share a finite check
before computing the 416(l) reduction bound or the 402(w)(2)(A) credit
window. NAWI and annual delayed-credit rates already reject non-finite
values through exact conversion; the two 36-month bracket checks already
reject them by equality. G does not consume the bundle's PIA factors, wage
base, four-year delayed-credit cap or default survivor reduction period.

Executed invariants in
`tests/test_track_b_gross_benefits_fix_round_3_rates.py` are:

- Every non-finite checked rate raises an input error before coverage
  refusal at the single-family, household and evaluated entry points;
  guarded household input errors leave every guard at its current month.
  The full example matrix and Hypothesis
  `test_nonfinite_rate_never_becomes_a_coverage_outcome` execute this.
- Finite rate encodings inside the existing tolerance produce exactly the
  same `StatutoryRates` fractions and provenance as the ordinary bundle.
  Hypothesis
  `test_finite_rate_tolerance_preserves_exact_statutory_fractions`
  executes this identity across all eight values.
- A non-finite FRA cannot produce a benefit or credit window.
  `test_nonfinite_full_retirement_age_is_an_input_error` and Hypothesis
  `test_nonfinite_full_retirement_age_never_produces_a_credit_window`
  execute the rejected values and cohort ranges.

Healthy-bundle controls retain the `non_aime_formula_pia` and
`combined_family_maximum` refusals and their denominators. No supported
monetary rule, rounding order or source-conflict default changes. The three
decision sites link the Axiom source-conflict ids in comments; the parent
counterfactual above now executes the $75 difference using a test-only
helper. No new source capture or published monetary example is introduced.

### Divorced spouse with an entitled child in care

RS 00615.010 exempts both spouses and divorced spouses from age reduction
in months with an entitled child in care. RS 00615.201A.2 states that with
RIB entitlement the spouse payment for such months is always the
unreduced spouse benefit less the reduced RIB. This implements the care
exemption in 202(q)(5); the available primary excerpt captures
402(q)(5)(A)(ii), while the direct 402(q)(5)(B) body remains an existing
source-inventory limitation. No additional direct-primary-source coverage
is claimed. A current-care divorced spouse retains its 403(a)(3)(C)
outside-maximum role, and its payment does not depend on ordinary method
B/C chronology or on auxiliary reduction months. The existing own-PIA
entitlement threshold and unsupported DIB sequencing are unchanged.

`child_in_care` now accepts a named entitled same-record child for a
`DIVORCED_SPOUSE`. `False` attests no current care, and `None` is unknown;
an entitled child on the record then requires an explicit attestation.
`first_entitlement_child_in_care` is a divorced-spouse-only Boolean or
unknown. RS 00615.201A.2 exempts all pre-FRA months if the child was in care
in the first month of divorced entitlement, and RS 00615.010 says that
exemption continues after the child's benefit terminates. Current care
settles the amount without that history. Without current care, an explicit
False initial-care attestation permits the ordinary aged formula. Unknown
or True initial-care history refuses as `divorced_spouse_care_history` if
the ordinary and exempt auxiliary payables differ. Conversion, FRA and ARF
history after care ends are outside this monthly snapshot. If the settled
payables are identical, missing history cannot change money and the month
remains supported. Different unused intermediate rates are disclosed in
the beneficiary note, with `age_adjusted_rate` showing the ordinary
diagnostic rate. Existing invented aged fixtures now explicitly attest no care
in either month; their expected amounts have not changed.

The reviewer's invented PIA $1,000, maximum $1,500 and own PIA $200 with
36 own reduction months give own RIB $160. The unreduced outside-maximum
spouse OB is $500, so the auxiliary payment is $340. The worker receives
$1,000 and the child $500, giving record total $1,840. This holds for both
direct `RecordState` and built `record_state`, auxiliary RF zero or 36,
and either entitlement order. Without current or initial care, ordinary
method C still pays $300 at RF zero and $225 at RF 36. The minimized
invented case has PIA $0.30, maximum $0.40, own PIA $0.10 and one own
reduction month: own RIB rounds to zero and the care auxiliary pays $0.10,
rather than the previous zero.

The new current-care formula is differentially checked against the
ordinary `SPOUSE_CHILD_IN_CARE` surface on a nonbinding maximum, and the
direct and built record paths are compared exactly. There is zero
rounding tolerance. The source-settled fixes do not reopen or change the
PR's existing needs-Max items, including rulings d1418 and d1338.

## Fix round 5 of October 14, 2026

The review's two findings are source-settled corrections. The existing
Needs Max's judgment items and rulings d1418 and d1338 remain unchanged.
No new capture, source erratum or published worked example is introduced.
Verification remains statutory conformance on invented cases only.

### Effective beneficiary cohort

RS 00615.003A.1 says, "People Born 1/1/38 or Earlier FRA for retirement
or spouse's benefits is age 65." RS 00615.010 states that RIB is reduced
by months of entitlement before FRA. With 402(q)(6)'s age-62 floor, the
1935 cohort therefore admits at most 36 own-RIB and spouse reduction
months. G previously lost that known cohort if the other duplicate
birth-year field was omitted. It could support RF37 or count the invalid
input as a GPO refusal with invented weight 7/3.

The validation pass now resolves one cohort and passes immutable copies
with that year to all own and auxiliary checks and computations. It also
preserves RS 00615.301B.2 widow periods and the pre-1929 method-D refusal.
The standalone `OwnBenefit` constructor still requires its own birth year
when delayed credits are positive; a later beneficiary cannot supply
metadata before that constructor runs. The new placement differential
covers validly constructed own benefits with zero delayed-credit months.

The reviewer case has survivor PIA $1,000, maximum $1,750 and own PIA $100.
RF37 now raises `InvalidFamilyInput` before GPO or payment; RF36 pays own
  RIB $80 and widow auxiliary $920 when GPO is absent. Both omission
directions, both equal fields and all five entry points are tested on
direct and built snapshots. The minimized positive-dime case, PIA and
own PIA $0.10 with RF37, is also invalid. RF36 with GPO through December
2023 retains the valid `government_pension_offset` refusal and weight 7/3.

The broader invariant generator formerly admitted the same invalid pairs:
a 1929 widow with own RF37 and an omitted own birth year, and a spouse
with auxiliary RF37 whose own delayed credits supply cohort 1929.
Hypothesis minimized and executed both. Its valid-family strategy now
draws own and auxiliary months within the effective cohort's legal bound;
the global own RF1-60 and auxiliary RF0-60 ranges remain reachable.
Every existing invariant assertion, published figure and invalid-input
test is retained. Invalid rows are not caught or filtered as refusals.

### Settled care-history payment

202(k)(3)(A) says the benefit "shall be reduced, but not below zero" by
the own benefit. The review's retirement PIA $1.10, maximum $1.60,
divorced-spouse own PIA $0.50, own RF36 and DRC48 produce own RIB $0.50
and spouse OB $0.50. Ordinary method C gives intermediate $0.40; the
care-exempt intermediate is $0.50 (RS 00615.201A.2). Both histories pay
zero after the own-RIB offset, so missing or protected initial-care
history now supports that settled payment. The own and auxiliary
whole-dollar amounts are both zero; the record pays only the worker's
$1.10, floored to $1.

The `age_adjusted_rate` field retains the ordinary $0.40 as a diagnostic;
the note explicitly records both intermediate alternatives. This
beneficiary is outside the maximum under 403(a)(3)(C), so the diagnostic
is excluded from both the subject total and `savings_clause_total`.
It cannot change another beneficiary's rate or a 403(a)(5) guard total.
The minimized auxiliary-RF witness is PIA $0.30, own PIA/RIB $0.10 and
one spouse reduction month: ordinary intermediate zero and exempt
intermediate $0.10 both pay zero. Both examples and the Hypothesis
payment differential pin the boundary; cases whose payables differ still
refuse as `divorced_spouse_care_history`, retain their weights and block
totals. The earlier $715 surviving-divorced caregiver and $340 current-care
divorced-spouse regressions remain exact.

## Fix round 6 of October 14, 2026

Verification class: statutory conformance on invented cases only. This
round introduces no population, behavioral or forecast claim, source,
published example, statutory interpretation or refusal code. The earlier
Needs Max's judgment items and rulings d1418 and d1338 remain unchanged.

### Cohorts across household records

The round-5 reviewer traced, but did not execute, a cross-record omission.
It reproduces at f4799e04: worker p on record A has PIA $100 and cohort
1935; worker q on B has PIA $1,000 and maximum $1,500. Person p is also
q's spouse with RF37 and declared own PIA $100, but no duplicate cohort.
December 2023 incorrectly pays p an auxiliary $298.30 ($298 whole dollars),
or counts a GPO refusal with weight 7/3. Supplying conflicting cohort 1960
on that declared own benefit produces the same incorrect result. Both
guards incorrectly advance to January 2024.

RS 00615.003A.1 fixes the 1935 person's FRA at 65, and 402(q)(6)'s age-62
floor permits only 36 spouse reduction months. The household now resolves
one cohort from all supplied worker, beneficiary and own-benefit years,
rejects conflicts even without delayed credits, and uses immutable copies
in both household entry points. Resolution works in either direction:
a beneficiary's known cohort also bounds their own worker record. All
family inputs are checked before any coverage refusal or guard advancement.

| Invented configuration | Result |
| --- | --- |
| Worker cohort 1935, spouse RF36, duplicate cohort omitted or equal | Supported: auxiliary $300; household $1,400, also $1,400 whole dollars |
| Same RF36 case, pre-2024 GPO flag | `government_pension_offset`; row and weight 7/3 retained |
| Worker cohort 1935, spouse RF37 | `InvalidFamilyInput`; neither guard advances |
| Worker cohort 1935, beneficiary or declared own cohort 1960, RF36 or RF37 | `InvalidFamilyInput` before GPO; neither guard advances |

The failing-first regressions cover both direct and built snapshots and
both household entry points. A positive-dime minimization, own PIA $0.10
and RF37, still raises. Hypothesis exercises all seven nonempty metadata
placements, own and auxiliary reduction bounds, reversed record order,
unchanged inputs, conflict priority, refusal weights and guard state.
The RF36 payment differential equals the standalone family computations
exactly; no rounding tolerance is admitted.

### Preserved care diagnostics

The equal-payable care-history diagnostic now appends to `row.note`, with
a separator only when an earlier note exists. No payment rule changes
(202(k)(3)(A); RS 00615.201A.2). The current entitlement function emits
nonempty notes only for unentitled rows, so this was a latent overwrite;
there is no current public-input example with an earlier entitled-row note.
The regression explicitly injects that note at the entitlement boundary
while retaining the real computation, using the earlier PIA $0.30 / own
RIB $0.10 / spouse RF1 case. Both intermediate histories pay zero.
Hypothesis proves the earlier text survives and every other benefit field
equals the unmodified diagnostic case, including the empty-note case.

These fixes extend invariants 6-8, 19 and 20. The retained source/hash,
registry, round-3/4/5, conformance-report and depletion-cut compatibility
checks continue to apply. Cohort resolution does not implement combined
family maximums or multiple auxiliary entitlement; both remain refused.

## Fix round 7 of October 15, 2026

Verification class: statutory conformance on invented cases only. This
round preserves all earlier controls and introduces no population,
behavioral or forecast claim. The earlier Needs Max's judgment items and
rulings d1418 and d1338 remain unchanged.

Worker cohorts now survive record construction independently of own-benefit
entitlement and record kind. The unclaimed 1935 worker's RF37 spouse row
raises `InvalidFamilyInput` in both household APIs, before GPO or any guard
advancement (402(q)(6); RS 00615.003/.010). RF36 pays $375 auxiliary and
$1,375 household total, or retains the valid GPO refusal and weight 7/3.
Direct and built records, cohort placements and record order agree exactly.

Positive own-RIB reductions for known cohorts before 1916 now refuse as
`own_rib_history_before_1978`, because RS 00615.005C.2 requires historical
PIA and money-reduction inputs that G does not carry. The review's 1912,
$1,000, RF1 case no longer reports the unsupported $994.40 result.
Its refusal stays in the separate 27-witness denominator; the fixed-cohort
356,400-cell lattice remains unchanged. Invariant 21 records the historical
scope, input-error priority and supported zero/no-reduction boundaries.

The own-RIB widow boundary remains conservatively at cohort 1929. The
design, module documentation and refusal diagnostic now distinguish that
implementation limit from the source's January 2, 1928 boundary
(RS 00615.010/.020B). The known 1928 over-refusal and the 1929 control,
$200 own plus $800 auxiliary, are explicit; no alternative statutory
interpretation was selected.


## Fix round 8 of October 15, 2026

Verification class: statutory conformance on invented cases only. No
population, behavioral or forecast claim, real data, new source capture or
published monetary example is introduced. The earlier $715 surviving-divorced
caregiver, $340 divorced-spouse caregiver, per-person and household cohort
controls remain required. Rulings d1418 and d1338 are unchanged.

### Identical validation at every entry point

Section 203(a)(2)(A), with the earlier-DIB exception in 203(a)(2)(D),
requires retirement eligibility no later than the insured person's age-62
year. The shared check now uses the resolved `worker_birth_year`, whether
or not the worker is entitled. Both `record_state` and the input-validation
pass used by family, household and guarded calculations call it.

The review's unclaimed cohort-1935 worker, eligibility year 1998, PIA
$1,000 and maximum $1,500, with a divorced spouse flagged for GPO in
December 2023, now raises `InvalidFamilyInput`. No weight is counted and
no guard advances. The same error occurs when both monetary fields are
zero. Eligibility year 1997 remains a valid GPO refusal with weight 7/3.

The differential also minimized an order disagreement to two zero-PIA
records: record-0 declared a non-AIME PIA and record-1 had a spouse with
GPO. The ordinary household path followed insertion order while the
monthly-outcome path sorted record ids. Both now compute in sorted record
order after validating every input, selecting the same refusal without
changing any payment rule. An invalid later record still raises before
an earlier record's coverage refusal.

Invariant 20 now includes eligibility/cohort consistency independently of
entitlement, exact canonical payment and refusal equality across the
builder, direct snapshot, household and monthly-outcome routes, preserved
inputs, and unchanged guards after errors. The new entry-point Hypothesis
tests generate unclaimed and deceased workers, missing and conflicting
cohorts, dual entitlement, GPO and multiple records. Multi-record comparisons
use the household APIs because standalone family computation cannot assert
cross-record consistency. Refusal equality uses the reason code; input
errors use the exception class. Supported comparisons use exact fractions
and whole-dollar amounts, with zero tolerance.

### Historical reductions for auxiliaries and survivors

RS 00615.005C.2 states that its money-history method applies in "all cases
involving single entitlement to actuarially reduced benefits prior to 1/78".
The required current money amount of reduction and current unreduced rate
are not supplied by this snapshot. A modern reduction factor alone cannot
recover their ratio. RS 00615.201 and .301 also distinguish historical
rounding: before June 1982, spouse benefits rounded upward and widow
reductions rounded downward. A modern rate of zero after rounding is
therefore not proof of a historically settled zero.

Reduced spouse and divorced-spouse entitlement can begin at age 62, so
cohorts before 1916 can predate January 1978. Aged widow entitlement starts
at 60, but RS 00615.310A states that DWB converts to reduced aged widow
benefits at FRA. DWB starts at 50; an aged widow or surviving divorced
spouse born before 1928 can therefore carry a pre-1978 disability history.
The inputs do not exclude that route. These auxiliary cases refuse as
`reduced_benefit_history_before_1978` when the relevant amount is unsettled.
Own RIB retains `own_rib_history_before_1978` and its age-62 boundary.

The coverage check conservatively propagates the full zero-to-unreduced-rate
interval for the missing historical reduction through the applicable own
benefit offset, RIB-LIM and child-care minimum. These are safe bounds, not
a claim that every endpoint is attainable for every dated award. It does
not invent historical money inputs or date an award from its current RF.
Zero reduction, no payable rate, current spouse care, a zero method-C
excess, and clipping that settles both endpoints remain supported. DWB has
an automatic reduction even when its input RF is zero.

For a beneficiary subject to the maximum, the pre-offset age-adjusted
amount must also be settled: it enters the 203(a)(5) savings-clause total
and may affect Parisi redistribution. An offset that merely hides its
variation in the current payable is insufficient. Outside the maximum,
an equal payable can be supported with any uncertain intermediate value
labelled as a diagnostic, preserving earlier notes. All input errors are
checked before these refusals; refused rows and weights remain in every
denominator and required totals block.

The review's cohort-1912 spouse, no own benefit, PIA $1,000, maximum $1,500
and RF1 formerly paid $496.50 ($496 whole dollars). The corresponding
widow with RF1/period 60 formerly paid $995.20 ($995 whole dollars).
Neither is a known historical payment. Both now refuse with the new reason
and retain weight 7/3. No replacement historical dollar figure is imputed.
The 356,400-cell conformance lattice is unchanged; the new executed
historical witness makes the separate refusal denominator 28.

Invariant 22 extends historical coverage to every reduced auxiliary role:
for each cohort and role, refuse exactly when pre-1978 entitlement is
possible under the declared coverage boundary and the conservative
missing-money bounds leave a relevant amount unsettled. The role/cohort
property, invalid-input property, settled-care and zero-excess differentials,
RIB-LIM exception, denominator checks and savings-clause regression execute
this contract. The envelope is deliberately conservative; it does not
certify a tight set of all possible dated histories. Narrower historical
support needs dated entitlement and reduction-money evidence.

### Needs Max's judgment: DWB after January 1984

The broad instruction in RS 00615.005C.2 is "all cases involving single
entitlement to actuarially reduced benefits prior to 1/78". In contrast,
RS 00615.301B.1.e says "all disabled widow(er)s under age 60 receive .715 of
the full unreduced WIB for 1/84 and later". RS 00615.005A.7 also states
that the 1983 amendments "Eliminated the additional reduction for the
period between age 50 and age 60." A specific-rule reading could treat
that change as settling the entire later amount, including earlier awards.
The general historical reading still requires the missing monetary ratio.

This round conservatively refuses an otherwise unsettled pre-1978-capable
DWB cohort and its possible aged-widow conversion; it does not assign a
historical payment. For cohort 1927 in January 1984, with invented PIA and unreduced rate
$1,000, the fixed 71.5% reading would pay $715.00 ($715 whole dollars), while the implemented
reading refuses and retains the row and weight. Tests pin the captured
texts, the alternative exact $715 formula and the actual refusal. This is
an explicit support-boundary judgment item, separate from the earlier
$715 surviving-divorced child-care regression, which remains supported.

Dual-entitlement snapshots also lack dates and earlier money history.
RS 00615.250 gives the current reduced-excess procedure and refers to
RS 00615.005F for subsequent adjustments, but the captured .005 has no
section F. The implementation conservatively refuses an unsettled old
auxiliary history; a zero reduced excess stays supported. It does not
claim that the conservative interval identifies a particular historical
dual-entitlement amount. Expanding that historical surface is not in scope.


### Needs Max's judgment: historical dual entitlement

RS 00615.005C.2 explicitly describes "single entitlement". RS 00615.020
states "Method C - First benefit calculated independently; reduce excess
of second benefit for age (if larger)." Applying that instruction directly
to the current excess suggests the modern calculation even for an old
cohort with an unreduced own benefit. The historical instruction instead
leaves the dated reduction-money history unresolved. RS 00615.240 explicitly
retains historical treatment for spouse-before-RIB awards: "For initial
entitlement to the reduced benefit prior to 1/78, separately reduce any
increases before 1/78 but apply the basic formula for post 1977 increases
in PIAs or spouse's original rate." That text does not settle every
own-first sequence.

For an invented cohort-1912 spouse with unreduced own RIB $400, spouse OB
$500 and auxiliary RF1, the current method-C reading pays auxiliary
$99.30 ($99 whole dollars), with own $400. The conservative implementation
refuses `reduced_benefit_history_before_1978`, retaining the row and weight;
it does not assign a different historical dollar amount. The source-quote
test executes that alternative and the cohort-1916 control side by side
with the historical refusal. Resolving this narrower historical dual
surface needs Max's judgment; no new monetary default is silently chosen.


## Fix round 9 of October 15, 2026

Verification class: statutory conformance on invented inputs and captured
source text only. This round admits input-error classification and
consistent refusal selection for the existing G surface. It introduces
no population, behavioral or forecast claim and no new monetary rule.

### Validate schema-declared input before deciding coverage

The design's §6 and §7 require valid unsupported family rows to remain in
coverage denominators. An invalid row is not a coverage observation.
The common validation layer therefore checks every public input field
before any coverage decision: the worker description, direct snapshot,
own benefits, beneficiaries, household records, conditions, payment month
and the guards' constructor inputs, mapping and expected month. It checks
the declared types and value ranges,
including exact enum classes and integers that exclude booleans, then the
existing date, cohort, role, amount and cross-record consistency rules.
Those existing rules derive from 202(q), 202(w), 203(a)(2) and 203(a)(5),
with the captured POMS instructions cited above; this refactor adds no
statutory eligibility or payment rule.

The review supplied two invalid families that previously produced a
coverage refusal and advanced a monthly guard. One mixed
`RecordCondition.ADMINISTRATIVE_FINALITY` with a `BeneficiaryCondition`
inside record conditions. The other supplied `birth_year=True` for a
widow. Each now raises `InvalidFamilyInput` before a refusal can be
selected, so its weight 7/3 is never counted and no guard changes.
The malformed-input properties extend this assertion to one-field
corruptions across the entire declared input surface, preserving the
valid seed families and the earlier input-before-refusal controls.

Calendar and cohort years use the representable calendar range 1–9999.
Guard advancement checks the successor month before changing protection
or history; December 9999 therefore raises an input error atomically.
`test_terminal_calendar_month_errors_leave_every_guard_unchanged` exercises
supported and refused computations through both guarded routes. Outcome
keys, weights and callbacks are checked before invoking computation.
Wrong-type errors remain catchable as `TypeError` for existing callers,
and also inherit `InvalidFamilyInput`, so every malformed declaration has
the same input-error contract. Monetary fields retain their documented
conversion to exact fractions; no valid numerical representation changes.
Whole-dollar AIME accepts an int or an integral Fraction, retaining the
existing direct/built DIB differential's exact representation. Booleans
and fractional-dollar AIME remain invalid.

| Configuration | Result in round 9 |
| --- | --- |
| Wrong enum class in a condition collection, boolean in an integer field, or another malformed input field | `InvalidFamilyInput`; no outcome, denominator contribution or guard advancement |
| Valid existing supported family | Existing exact payment and whole-dollar fields |
| Valid existing unsupported family | Existing refusal reason, with its row and weight retained |
| Retirement record, eligibility 1982, zero PIA/maximum/own benefit and `NON_AIME_FORMULA_PIA` | `eligibility_before_1983` on every route |

The last row previously selected `eligibility_before_1983` for a direct
snapshot and `non_aime_formula_pia` for a built snapshot. Both now use one
record-refusal order: eligibility before 1983, conditions sorted by their
values, then historical DIB entitlement. The pre-1983 boundary remains a
coverage limit; this change only makes reason selection independent of
construction style. Invariants 23 and 24 above state the new executed
contracts. The extended round-8 differential includes historical cohorts
and combined conditions, comparing exact refusal reasons as well as
supported payment fields.

### Correct the disabled-widow pinpoint citation

The captured RS 00615.301 places the instruction that disabled widow(er)s
under age 60 receive .715 of unreduced WIB from January 1984 under
B.1.e, "Additional reduction for months prior to age 60". Both the
module documentation and the earlier judgment item now cite
RS 00615.301B.1.e. The separate RS 00615.310B.3 provision remains
"1/84 DWB Recalculation". The regression
`test_disabled_widow_instruction_is_under_captured_b1e_and_b3_is_separate`
checks each quote within its actual captured HTML section, and
`test_disabled_widow_citation_matches_capture_in_design_and_module`
checks both documentation locations while retaining the .310 citation.
The corrected pinpoint does not settle the historical DWB interpretation
already listed under "Needs Max's judgment" and changes no amount.

### Not in scope

The round changes no supported monetary formula, historical support
boundary, source capture or protected evidence artifact. The earlier
historical DWB and dual-entitlement judgment items remain open. No new
statutory reading is selected.


## Fix round 10 of October 16, 2026

Verification class: statutory conformance. Admitted scope remains supported
invented and captured statutory cases only; no population, behavioral or
forecast claim. No supported amount, statutory formula, refusal code or
source capture changes.

### Validate objects and every exported helper

All public input dataclasses validate at construction, including
`dataclasses.replace`. Result construction was validated in round 10;
round 11 below restricts it to G and rejects public replacement or copying. Result validation covers nested rows,
nonnegative finite dime amounts, whole-dollar pairs, exact enums and
booleans, calendar years, nonempty identifiers, and payment and denominator
identities. Mappings are copied to immutable views. A refusal requires an
`UnsupportedReason`, never a similarly named `BeneficiaryCondition`.
These are the design's §6–7 input/coverage distinction and the existing
202(q), 203(a), 215(g) and exact-arithmetic rules, not new entitlement rules.

The review's malformed refusal, `beneficiaries=None` result replacement,
and negative `record_total` replacement now raise `InvalidFamilyInput`
at construction. Aggregates defensively validate all rows before counting
or deciding whether coverage blocks a total. A malformed later row cannot
be hidden by an earlier valid refusal.

The exported maximum, COLA, age, rounding, redistribution and aggregate
helpers apply the same error class. Boolean PIA with eligibility 1982
raises before `eligibility_before_1983`; no weight 7/3 enters a denominator.
`applicable_cola_percents` revalidates calendar fields and all supplied
COLA entries before its coverage check. Signed dime rounding remains
supported for internal residual calculations; payable amounts and weights
remain nonnegative. Existing exact-number conversions remain supported.
Consumed parameter series also validate their shape, year keys and finite
nonnegative values before coverage; a negative delayed-credit rate can no
longer decrease an old-age benefit. Missing observations keep their
documented lookup error. The two prior tests requiring precisely the base
`ValueError` now require
precisely its `InvalidFamilyInput` subclass; their diagnostic checks remain.
Earlier widow-period tests now include construction inside their existing
invalid-input assertions. Their full cohort/month domains and supported
payment assertions remain unchanged.

`SavingsClauseGuard.admit` and `.evaluate` validate the complete nested
result or refusal before carrying protection, recording history or
advancing the month. Invalid input leaves all guard attributes unchanged.
A valid unsupported month still advances and retains its row and weight.
`admit` preserves its return-identity contract while storing the validated,
normalized copy in its history; changing the caller's original object cannot
poison a later month. No 203(a)(5) interpretation changes.

| Configuration | Result |
| --- | --- |
| Malformed public declaration, result, refusal, helper argument or nested outcome | `InvalidFamilyInput`; no observation, denominator contribution or guard change |
| Existing valid supported configuration | Identical exact and whole-dollar payments |
| Existing valid refused configuration | Identical `UnsupportedReason`, retained row and weight |

### Bind registry citations to their captured sections

RS 00615.768's two examples now cite F.1 and F.2, under the captured
`F. EXAMPLES`, instead of E.1 and E.2. The zero-payable spouse example
retains PIA $400, maximum $650, own $100, standard shares $83.30 and
redistributed child shares $125. The partial-payable child example retains
PIA $600, maximum $900, own $120, partial payable $30 and redistributed
rate $270. All six and five quoted figures remain unchanged.

The same audit corrects RS 00615.736B.3 labels: captured example 1 includes
both the 1979 and 1981 formulas; the next two registry cases are examples
2 and 3. The amounts and the pre-1982 historical upward-rounding refusals
remain unchanged. Every registry entry now checks its actual section
heading and boundaries, in addition to the existing figure, byte-hash,
source-erratum and monetary checks. Regeneration changes only the report's
registry file hash; its invented classification counts remain identical.

### Not in scope

No new module, population data, source retrieval, monetary rule or
statutory interpretation is introduced. Earlier Needs Max's judgment
items and rulings d1418 and d1338 remain unchanged. Input constructor
checks establish structural validity. Round 11 below closes the separate
result-provenance gap by admitting only sealed G computations. Calendar, cohort and
family rules that require a parameter bundle still run at the entry point.

## Fix round 11 of October 16, 2026

Verification class: statutory conformance. Admitted scope remains supported
invented and captured statutory cases only, with no population, behavioral,
payment-timing or forecast claim. This round changes no supported dollar
amount, source capture, refusal code or statutory interpretation.

### Seal computed results and coverage outcomes

`BeneficiaryBenefit`, `FamilyBenefits`, `HouseholdBenefits`, `FamilyOutcome`,
`FamilyDenominator` and `FamilyConfigurationUnsupported` now require G's
private construction capability. Public direct construction,
`dataclasses.replace`, `copy.copy` and `copy.deepcopy` raise
`InvalidFamilyInput`, even when the supplied fields look consistent. Input
declarations remain constructible and replaceable. Public result fields
and dataclass equality remain available. Round 13 removes serialization:
every pickle protocol and `copyreg` path raises `InvalidFamilyInput` for
sealed values. Persist declared inputs and recompute the result. This is
an API provenance contract, not a security boundary against Python code
accessing private internals.

Each seal binds the object identity and a type-sensitive immutable snapshot
of its fields, including nested results. Every coverage, savings-clause,
weighted-total, household-total and report consumer requires an unchanged
seal. Altered or unsealed results raise before contributing a denominator
row or changing guard state. The guard retains its own detached sealed
history, so bypassing frozen fields on a caller's old result cannot change
the next month's protection. Valid refusals retain their reason, row and
weight. The conformance report's supplemental witnesses also go through
`evaluate_family`, which verifies refusal provenance.

Sealing retains field validation and adds the derivable identities:
auxiliary payable is `max(0, age_adjusted_rate - own_benefit)` under
202(k)(3)(A); original, standard, redistributed and counted amounts obey
203(a)(4) and the original-benefit caps; outside beneficiaries consume no
maximum under 203(a)(3)(C); non-entitled beneficiaries have zero auxiliary
rates; available maximum, original-benefit totals, binding and redistribution
flags, proportional standard shares, subject totals and payment totals
reconcile. Whole-dollar pairs still follow 215(g). A widow's child-in-care
floor can exceed her own proportional share (RS 00615.340/.010), so no false
`age_adjusted_rate <= family_maximum_rate` bound is imposed.

The review's minimized invented case has a retired-worker PIA of $1.10,
maximum $1.90 and two children. Each child's share is $0.40 and the January
record total and protected total are $1.90. February's PIA is $1.20 with the
same maximum; dime rounding gives $0.30 to each child and total $1.80. The
unchanged 203(a)(5) guard refuses February, leaving one supported and one
refused row. Replacing one January child's age-adjusted rate with zero while
retaining its $0.40 payable now raises `InvalidFamilyInput`. These invented
figures are executable counterexamples, not figures attributed to SSA.

### Use one role and record compatibility table

The same immutable table governs beneficiary declarations, family validation,
seal-time role checks and `original_benefit`, the sole exported helper with
both role and record-kind arguments. The table follows 202(b)-(h):

| Roles | Record kinds | Role-specific original-benefit arguments |
| --- | --- | --- |
| Spouse, spouse with a child in care, divorced spouse | Retirement, disability | Neither alternate basis nor parent count |
| Child | Retirement, disability, survivor | Neither alternate basis nor parent count |
| Widow(er), surviving divorced spouse, disabled widow(er) | Survivor | Optional basis at least the death PIA, under 202(e)/(f)(2)(B)-(C) |
| Mother/father | Survivor | Neither alternate basis nor parent count |
| Parent | Survivor | Optional count one or two, under 202(h)(2), RS 00209.015 |

An omitted or `None` parent count means one for a parent. Supplying a count
for any other role is invalid; the family computation passes the count only
to parents. A non-widow basis is invalid even if it equals the PIA. The
review's widow/retirement helper call and child/survivor call with PIA $1,000
and basis $2,000 now raise `InvalidFamilyInput` rather than returning $1,000
and $750. Compatible calls keep precisely the family entry point's original
benefit, including parent, widow-basis and dime-rounding cases.

| Configuration | Result |
| --- | --- |
| Unchanged result or refusal produced by G | Existing payments, coverage and denominator behavior |
| Public result/refusal construction, replacement or copying | `InvalidFamilyInput`; no coverage refusal code |
| Unsealed or altered result at any consumer | `InvalidFamilyInput`; no row, weight or guard change |
| Incompatible role/record, non-widow basis or non-parent count | `InvalidFamilyInput` before any coverage refusal |
| Existing supported or refused statutory configuration | Same amount or `UnsupportedReason`, with every refusal retained |

### Executed invariants

27. **Computed-result provenance and accounting closure.**
    `test_only_g_computation_can_construct_results` and
    `test_property_public_copy_cannot_create_sealed_outputs` cover all six
    sealed types. `test_every_consumer_rejects_unsealed_or_altered_results`,
    `test_property_changed_outcome_never_counts_or_advances` and
    `test_report_witnesses_require_sealed_refusals` cover consumers and
    denominator/guard atomicity. `test_guard_history_is_detached_from_caller_result`
    and `test_review_altered_age_rate_cannot_lower_savings_clause_protection`
    preserve the protected total and coverage counts.
    The sealed accounting property,
    `test_property_seal_time_reconciles_family_accounting`,
    `test_property_seal_time_bounds_beneficiary_rates`,
    `test_seal_time_reconciles_binding_and_proportional_rates` and
    `test_seal_time_rejects_inconsistent_computed_payable` execute monetary
    identities independently of the public construction barrier.
    Round 13's serialization-denial tests reject every pickle protocol;
    `test_derived_public_totals_and_status_require_unchanged_seals`
    protects computed properties. Earlier control assertions remain, with
    valid outputs obtained from public computations and comparison-only
    replacements expressed as comparisons over every public field. The earlier
    guard-history control now explicitly rejects changing a computed PIA
    from a Fraction to an equivalent numeric string; it retains both the
    return-identity and detached-history assertions on a genuine result.
28. **Role/record and argument equivalence.**
    `test_every_exported_role_record_helper_has_a_compatibility_property`
    inventories exports. Hypothesis over each of the 27 role/record pairs
    in `test_role_record_helpers_match_family_original_amounts_or_input_errors`
    proves invalid-before-refusal and exact helper/family/independent-share
    agreement (zero tolerance). `test_every_nonwidow_basis_is_invalid_in_helpers_and_family_declarations`,
    `test_parent_count_is_invalid_for_every_nonparent_role`,
    `test_widow_basis_below_pia_is_invalid_on_every_route` and
    `test_two_parents_do_not_pass_their_count_to_other_survivor_roles`
    execute the applicability, basis-bound and mixed-family properties.

### Needs Max's judgment and not in scope

No new statutory choice arises. All earlier judgment items, conservative
refusals, source-erratum controls and rulings d1418/d1338 remain unchanged.
This round does not implement savings-clause raised payments, new family
configurations, new sources or real-data processing.

### Existing property counterexample found by the full gate

The full gate found an unstated premise in
`test_a_reduced_joiner_after_a_cola_is_refused_iff_the_total_falls`: it
unconditionally admitted the intervening COLA month. Hypothesis minimized
the case to a survivor PIA $2.00, maximum $3.30, two unreduced widows and a
mother/father. Their rates are $1.20/$0.90/$1.20. A 5% COLA gives PIA $2.10
and maximum $3.40, but proportional dime flooring gives
$1.20/$0.80/$1.20, a total of $3.20. The guard correctly refuses under the
existing 203(a)(5) reading. The reviewed head and current implementation
were executed side by side and produce identical amounts and refusal.
This is an intended rounding counterexample to the test's admission premise,
not a changed supported amount or a new statutory default.

The same property now includes this reduced case as a Hypothesis `example`.
Every original joiner-month assertion remains for admitted COLA months.
The additional branch verifies the earlier PIA increase, qualifying maximum,
actual decline, exact protected total and continuing refusal after the joiner.
No generated case is discarded or weakened to make the property pass. This
extends invariant 9's executed coverage without adding a collected test node.

## Fix round 12 of October 16, 2026

Verification class: statutory conformance. This integration admits only
invented and captured statutory cases, with no population, behavioral,
payment-timing or forecast claim. It changes no statutory amount, refusal
reason or source capture. It preserves the round-11 construction contract
while integrating the merged R2 and R3 implementations.

### Shared provenance and layer boundaries

`track_b/_provenance.py` holds one package-private capability and the declared
result and refusal classes. G, R2 and R3 use that same capability internally;
it is never a public constructor parameter or exported API. Direct
construction, `dataclasses.replace`, `copy` and `deepcopy` of computed results,
refusals, outcomes and denominators raise `InvalidFamilyInput`. The seal
binds exact type, object identity and recursively captured field values,
including nested results, mappings and sets of credited months. Round 13
prohibits pickling and removes restoration helpers. Persistence stores
declared inputs and recomputes results. This remains an API contract, not a
security boundary against private Python internals.

There is one catchable refusal family and one declared reason enum per layer:

| Layer | Declared refusal class | Exact reason enum |
| --- | --- | --- |
| G | `FamilyConfigurationUnsupported` | G `UnsupportedReason` |
| R2 | `RETConfigurationUnsupported` | `RETUnsupportedReason` (also available under R2's original `UnsupportedReason` alias) |
| R3 ARF | `ARFConfigurationUnsupported` | `ARFUnsupportedReason` |
| R3 recomputation | `RecomputationConfigurationUnsupported` | `RecomputationUnsupportedReason` |

All classes retain code `FAMILY_CONFIG_UNSUPPORTED`. Each evaluator catches
this common family, including a genuine upstream refusal, without recasting
its reason. Each declared class accepts exactly its bound enum at its
private computation boundary. Metadata and input errors raise before a
callback can produce a coverage row.

`count_family_outcomes` is the sole denominator implementation. It accepts
sealed `FamilyOutcome`, `RETOutcome`, `ARFOutcome` and
`RecomputationOutcome` rows, checks provenance before counting, rejects
duplicate keys, and retains every refused row and weight, including zero
weights. `count_arf_outcomes` and `count_ret_outcomes` delegate to it;
`RETDenominator` aliases `FamilyDenominator`. Counts and weights partition
exactly into supported and refused totals and the per-reason inventory.

The result boundary is narrower than the denominator boundary. Each evaluator
accepts only its own exact result type and unchanged seal. `apply_arf` also
checks a prior `ARFResult` before using its claim as an input. G household
aggregation, its money totals and the 203(a)(5) guard accept only G results;
G money totals accept only G outcome envelopes. R2 and recomputation money
aggregates likewise require their own outcomes. The guard and G conformance
report's refusal inventory accept only G's exact refusal class and reasons.
None of the common denominator machinery converts an ARF or recomputed PIA
into a family payment.

Seal-time identities retain G's 202/203 accounting. R2 validates the existing
203(b)/(f) gross/net/deduction and final/provisional reconciliation identities.
R3 validates the 202(q)(7) credited-month and benefit identities and the
215(f)(4) recomputation threshold. The original supported/refused tables and
all existing statutory readings remain in force; malformed provenance is an
input error with no coverage reason code.

### Executed cross-layer invariants

29. **Exact refusal binding and retention.**
    `test_each_refusal_has_one_exact_layer_reason_enum` and
    `test_every_evaluator_retains_a_genuine_refusal_family` exercise every
    layer and evaluator. `test_g_guard_and_report_reject_sibling_refusal_reasons`
    preserves G's reason inventory and guard boundary.
30. **One conserved, order-independent denominator.**
    `test_common_denominator_partition_order_and_layer_counter_differential`
    generates weights with Hypothesis, compares all counters with zero
    tolerance, reverses row order and verifies exact count/weight partitions.
    `test_common_counter_rejects_unsealed_or_altered_outcomes` covers every
    layer. Duplicate-key rejection and zero weights retain their existing
    semantics.
31. **Provenance and serialization closure.**
    `test_all_layer_outputs_require_the_shared_private_capability` and
    round 13's cross-layer serialization tests cover construction, copying
    and pickle denial. The shared
    tests also mutate nested credited months and transplant a seal to a
    different object. Existing round-11 Hypothesis tests continue to execute
    G's accounting and detached guard-history invariants.
32. **Layer-specific monetary admission and input-error atomicity.**
    `test_g_money_consumers_reject_other_layer_results_and_outcomes`,
    `test_invalid_evaluator_metadata_precedes_computation` and
    `test_invalid_computation_is_never_a_denominator_row` keep the money
    boundaries and invalid-before-coverage ordering. R2 and R3's design notes
    name their result/accounting property tests and evaluator checks.

### Widow and entitled CDB regression

The existing R2 binding-survivor-maximum case now explicitly attests
`child_in_care=False`, the assumption behind its original expected amounts.
All original assertions remain. The positive-care reading names the entitled
child (`child_in_care="cdb"`), as required by G's input schema. Both readings
compute widow $796.40, entitled CDB $0 and a binding maximum, and both retain
R2's `deduction_before_reduction_part_b` refusal. Boolean `True` is separately
pinned as `InvalidFamilyInput`; it does not name an entitled child. No care
rule or money reading is changed (202(q)(5)(D); RS 00615.340/.010).

### Source seal, judgment and scope

G, R2 and R3 were already excluded from the historical birth-evidence source
seal. The private provenance module is added to that same exclusion tuple
and its test mirror, and to the Track B module set whose disjointness from
the birth-evidence import graph is checked. No historical production source
or committed run is changed.

No new statutory interpretation needs Max's judgment. Earlier open judgments
and rulings remain as documented. The G conformance report must regenerate
byte for byte; all captured-source hashes and worked-example assertions stay
unchanged. This integration does not expand statutory coverage or implement
monthly assembly I.

R2's `GraceYearDecision` is also sealed computation evidence: it determines
protected months and therefore money under 203(f). `RETBeneficiary`,
`RecordYear` and `apply_ret_year` validate both final and estimated grace
evidence before coverage checks, including evidence altered after an input
record was constructed. `GraceYearState` remains a constructible declaration
of starting history. `test_every_ret_admission_rejects_invalid_grace_evidence`
and the grace serialization-denial and tamper-rejection property execute
this boundary. Seal-time validation tests call the private computation
capability explicitly to reconcile grace categories, eligible/protected
months and carried history; no public restoration path exists.
Malformed or deleted result fields are likewise input errors, as exercised by
Hypothesis `test_deleted_outcome_fields_are_input_errors`.

## Fix round 13 of October 16, 2026

Verification class: statutory conformance. Admitted scope remains invented
and captured statutory cases, with no population, behavioral or forecast
claim. No amount, refusal code, source capture or published worked example
changes in this round.

### Detached guard history and public snapshots

`SavingsClauseGuard` copies each admitted result and each skipped calendar
month into private history. Its calendar properties and `protected_total`
return fresh values. Caller-held objects can therefore be altered with
`object.__setattr__` without changing subsequent continuity, the protected
total or any coverage decision. `evaluate` also copies the outcome weight
before invoking the computation, so a callback cannot change an already
validated weight or create a metadata error after the guard has advanced.
Guard subclasses and uninitialized guards
are invalid inputs. Guards cannot be copied or serialized; persisted work
stores declared inputs and recomputes the monthly path.

The reviewer's invented January–March case gives a January retirement PIA
of $1.10, maximum $1.90 and one child's total of $1.60, with no binding
maximum. February adds a second child and totals $1.90 under a binding
maximum. March raises the PIA to $1.20 with the same maximum and totals
$1.80. Altering the returned February `next_month` snapshot to March cannot
skip February. Supplying March at that point raises `InvalidFamilyInput`.
After admitting February, March retains its $1.90 protection and its
`savings_clause_403a5` refusal (203(a)(5); POMS RS 00615.801B.2). Explicitly
skipping February retains the existing `savings_clause_history_unknown`
reading. No amount or savings-clause interpretation changes.

### COLA rounding counterexamples

The available formula maximum is monotone under a COLA, but separately
dime-rounded proportional shares can sum to less (215(i)(2)(A)(ii);
203(a)(4); POMS RS 00615.756). Two invented witnesses now replay the
reviewer's exact draws through the corrected formula-maximum property:

| Family and COLA | Before | After |
| --- | --- | --- |
| Two unreduced widows and a mother/father; eligibility 2026; 2.3% COLA | PIA $4.40, maximum $6.60; shares $2.40/$2.40/$1.80; total $6.60 | PIA $4.50, maximum $6.70; shares $2.40/$2.40/$1.70; total $6.50 |
| One parent and three children; eligibility 2025 PIA $17.10, prior COLA 6.5%; additional COLA 0.6% | PIA $18.20, maximum $27.20; shares $7.30/$6.60/$6.60/$6.60; total $27.10 | PIA $18.30, maximum $27.30; shares $7.20/$6.60/$6.60/$6.60; total $27.00 |

Both later months are refused under the unchanged 203(a)(5) guard, and both
refused rows and their full weights remain in the denominator. Parents are
now included in the general survivor-beneficiary generator. No previously
generated case is discarded by the corrected assertion. The widows'
original benefits are $4.40/$4.40/$3.30 before and $4.50/$4.50/$3.30 after;
whole-dollar payments sum to $5 in each month. The parent's family has
original benefits $15.00/$13.60/$13.60/$13.60 before and
$15.00/$13.70/$13.70/$13.70 after; whole-dollar payments sum to $25 in each
month. These invented examples pin the pre-whole-dollar total protected by
the guard, as well as the separate whole-dollar payment fields.

### Executed guard invariants

33. **Detached state and decision determinism.**
    `test_guard_every_public_snapshot_is_detached` mutates all five public
    properties and compares the next decision with an unmutated twin.
    `test_guard_admitted_objects_cannot_change_later_decisions` does the
    same for constructor inputs, admitted and evaluated results, skipped
    months and PIA arguments.
    `test_guard_detaches_weight_before_calling_computation` mutates the
    caller's numeric weight inside the callback and preserves the original
    denominator weight. `test_review_next_month_mutation_cannot_skip_qualifying_february`
    pins continuity and exact protection. Numeric-subclass rejection or
    canonicalization is pinned by
    `test_review_live_fraction_cannot_change_qualifying_pia_increase`.
    `test_guard_rejects_uninitialized_instances_at_every_public_entry`,
    `test_guard_rejects_undeclared_subclasses` and
    `test_guard_denies_copy_and_serialization` cover uninitialized state,
    subclasses, shallow/deep copies, every pickle protocol and `copyreg`.
34. **Available-room monotonicity, exact protection and denominator retention.**
    `test_formula_maximum_colas_preserve_available_room_and_guard_contract`
    generates every family kind, parents included, and checks monotone
    available room, exact protection after a qualifying PIA increase,
    refusal exactly when a governed total falls, and exact count/weight
    partitions. `test_review_formula_cola_rounded_decline_exercises_property`
    pins both reviewed rounding witnesses. These are intended violations of
    rounded-total monotonicity; they are not amount regressions.

### Supported and refused configurations

| Configuration | Result |
| --- | --- |
| Unchanged monthly path and supported family | Identical amount and guard decision |
| Altered caller-held input or returned guard snapshot after admission | Identical later decision to an unmutated twin |
| Attempt to omit a month through a changed snapshot | `InvalidFamilyInput`; guard remains at the required month |
| Qualifying PIA increase and lower governed rounded total | Existing `savings_clause_403a5` refusal; full denominator row and weight retained |
| Skipped qualifying history | Existing `savings_clause_history_unknown` refusal |
| Uninitialized/subclassed guard, guard copying or guard serialization | `InvalidFamilyInput`; no coverage refusal code |

### Needs Max's judgment and not in scope

No new statutory interpretation is selected. Earlier judgment items and
conservative savings-clause readings remain unchanged. This round does not
implement raised savings-clause payments, monthly assembly I, new source
captures or population processing.

### Shared declaration and result boundaries

Verification remains statutory conformance on invented and published cases.
These changes alter input admission and object ownership, without changing
any monetary formula, supported statutory configuration, or refusal reason.
The unchanged Act 203/215 computations are still exercised by the complete
conformance report and the R2/R3 differential against `origin/master`.

G, R2 and R3 use `_provenance._exact_number` for exact numbers. Numeric
subclasses are rejected rather than retaining caller-defined arithmetic;
`bool` is rejected in numeric slots. Accepted money is a fresh built-in
`Fraction` whose numerator and denominator are validated built-in integers.
Seals store those integer components, never the caller's live number.
Integer calendar and count slots retain their strict built-in integer types.
The boundary also rejects text and collection subclasses; declared enums
retain their exact enum identities. Existing float parameter encodings are
preserved before each layer's statutory cross-check.

Every public calculation rebuilds the complete declared input tree through
its constructors before considering coverage. Registered declaration classes
reject subclass construction. Nested inputs and defaults are rebuilt before
constructor logic can inspect them. The external `SSAParameters` class has
no validating constructor, so the shared boundary additionally checks every
field's declared structure and finite numeric encodings, including unused
fields. Each layer retains its existing statutory range checks. An invalid
alteration raises `InvalidFamilyInput`; a valid alteration computes exactly
as a fresh declaration. It creates no refusal or denominator row merely
because some other field requests an unsupported configuration.

All sealed results, refusals, outcomes and denominators reject every pickle
protocol, `__reduce__`, `__reduce_ex__`, and the `copyreg` state path with
`InvalidFamilyInput`. Restore helpers were removed. To persist work, store
declared inputs and recompute. Tests of internal accounting validation call
the private computation capability explicitly; that capability is not a
public input or persistence API. Uninitialized refusals are checked for a
seal before their reason is read. A refusal with another layer's reason
cannot become a counted row.

`FamilyBenefits.by_id()` and R2's beneficiary-ledger accessor return detached
sealed rows. Altering those snapshots cannot change the original result.
Direct mutation of a sealed result or its fields still invalidates that
result at every consumer. R2 and R3 are functional computations: declarations
used to carry state are rebuilt on the next call, and no hidden controller
retains caller-owned history.

The additional executed invariants are:

- Numeric admission is canonical or rejected, and mutation of the original
  number cannot change weights, sums, denominators or guard decisions:
  `test_mutable_weight_cannot_change_denominator_or_aggregate`,
  `test_builtin_fraction_inputs_are_detached_before_admission`,
  `test_g_numeric_arguments_canonicalize_or_reject_mutable_subclasses`,
  and the complete SSA numeric-leaf matrix.
- No sealed value can be serialized: the all-type/all-protocol audit,
  `test_sealed_values_reject_every_pickle_protocol`, and
  `test_arf_1959_1960_pickle_patch_is_blocked_at_serialization`.
- Invalid declared fields precede coverage, while valid altered inputs agree
  with freshly constructed declarations: the G round-10 argument/field
  matrix and the round-13 R2/R3 field and Hypothesis mutation matrices.
- Every public result accessor validates provenance; detached row accessors
  leave the original result unchanged when their returned row is altered:
  `test_every_result_accessor_rejects_unsealed_public_fields`,
  `test_family_by_id_returns_detached_beneficiary_rows`, and
  `test_ret_beneficiary_accessor_returns_detached_sealed_rows`.
- Uninitialized, subclassed, changed or wrong-layer sealed evidence never
  enters a denominator: the all-sealed-type audit, nested-row properties,
  `test_uninitialized_refusal_is_an_input_error`, and round-12 cross-layer
  accounting properties.

No new statutory interpretation needs judgment. Existing d1418/d1338
boundaries and the judgment items elsewhere in this note remain unchanged.

The external SSA parameter boundary checks each raw field through its
schema before building the owned snapshot. Custom mappings are rejected
before their iteration methods can run.
`test_ssa_parameter_validation_checks_the_actual_mapping_snapshot` pins this
case. Raw condition elements in grace, ARF and recomputation are validated
before set deduplication; equality with a legal enum does not admit another
type. These are input-contract checks and change no statutory amount.

Malformed recursive declarations and sealed-state trees also raise
`InvalidFamilyInput`. This includes a declared numeric field pointing back
to its enclosing declaration, a COLA list containing itself, a denominator
mapping pointing to its denominator, and a sealed outcome weight pointing
to its row. Mapping traversal that produces an unhashable key is likewise
an input error. The translation is confined to declared-tree reconstruction
and seal-payload validation: an error raised by the computation callback
still propagates as a programming error. No coverage refusal or denominator
row absorbs these malformed inputs.

The executed invariant is that malformed traversal cannot bypass the shared
input-error contract, independently of the statutory layer.
`test_cyclic_declared_number_is_input_error`,
`test_cyclic_cola_collection_is_input_error`, and
`test_cyclic_denominator_state_is_input_error` pin the minimized G cases.
`test_cyclic_r2_r3_declarations_are_input_errors_before_refusal` and
`test_cyclic_sealed_rows_are_input_errors_in_every_layer` extend them across
RET, ARF and recomputation.
`test_malformed_mapping_traversal_is_input_error` pins the custom mapping;
`test_callback_recursion_error_remains_a_programming_error` protects the
distinction between malformed input and a computation bug.

The seal snapshot includes the declared result class as well as every field.
Changing an outcome's `__class__` to another layer's declared outcome cannot
reuse the original seal, even when both dataclasses have identical field
names. `test_seal_binds_the_declared_outcome_class` checks every ordered pair
of layers, both supported and refused rows, and generated exact weights.


Type admission uses identity, including numeric leaves, declaration classes,
sealed classes and parameter collection shapes. A numeric subclass whose
metaclass claims equality with a built-in type cannot enter a declaration,
seal or denominator. The existing mutable-number audit now combines that
attack with mutable public state. Its
`test_nested_ssa_and_ret_parameter_numbers_are_rejected_before_refusal`
property pins both the historical-coverage precedence case and a tampered
whole-dollar result field. The complete numeric-leaf and public-argument
matrices use the same stronger fixtures. No statutory amount or refusal rule
changes.


The same identity rule applies to G's condition collections, AIME encodings
and nested outcome-result classes. A custom iterable whose metaclass claims
to be a set cannot drop a condition between validation and construction.
The existing `test_declaration_subclasses_cannot_override_constructor_validation`
cases for `Beneficiary`, `WorkerRecord` and `RecordState` retain their original
subclass assertions and additionally pin this changing-iterator attack.

## Deduction before reduction

Verification class remains statutory conformance on invented and published
cases. `family_benefits_after_deductions(state, beneficiaries, *,
payment_month, params, deductions, households, standalone,
worker_deductions=None)` and `household_benefits_after_deductions(records,
*, payment_month, params, deductions, households, worker_deductions=None)`
implement Act 203(a)(4), first sentence, and GN 02603.020/.040/.050.
Both return the existing sealed family or household result. `deductions`
is a dictionary keyed by beneficiary ID, with `BenefitDeduction(reason,
payable=0, permanent=True)` values. `payable` is an exact nonnegative
`Fraction` after the deduction. `households` maps beneficiary IDs to
nonempty household IDs for the month; every beneficiary must be supplied
when an event is temporary. Ordered beneficiary lists retain their order;
dictionaries retain associations. Types, enum identities and every raw
container entry follow the existing public schema. `worker_deductions`
optionally reserves the number holder's charges against auxiliaries; those
charges do not release room (GN 02603.040B; RS 02501.155B.3.c).
For a spouse's `NO_CHILD_IN_CARE` event, `under_full_retirement_age=True`
is required and the supplied spouse benefit must be unreduced for age.
Act 203(c)(2) limits this deduction to a spouse "under retirement age"
whose benefit "was not reduced under the provisions of section 202(q)";
20 CFR 404.421(a) likewise excludes the reduced-benefit election month.
Missing or false age attestation, age-reduced spouse benefits and declared
current care are `InvalidFamilyInput` before a family or household refusal.
The attestation must also agree with a supplied birth cohort. SSA cohorts
run from January 2 through January 1 of the following year, with age
attained the day before the birthday (RS 00615.003/.010). If the payment
month is at or after even that cohort's latest possible FRA month, an
under-FRA attestation is impossible and invalid; an unknown birthday inside
the cohort's FRA interval remains a caller-attested fact. A 1950-cohort
spouse in January 2024 therefore cannot lose its $2 ordinary benefit under
a falsely attested no-care event on PIA $4/MAX $6.
Mother/father deductions under 203(c)(3)-(4) have no spouse age condition.

| Configuration | Result |
|---|---|
| No deductions | Exactly the existing family or household result |
| Auxiliary or survivor own earnings deduction, full or partial | Supported |
| Permanent deduction | GN 02603.050C redistribution |
| Estimated own earnings deduction | Same-household increase; other households retain their previous rate |
| No child in care, full deduction | Supported for an unreduced spouse with an explicit under-FRA attestation, or a mother/father |
| Dual entitlement | Existing Parisi computation, including zero technical rates |
| Workers' compensation offset | `workers_compensation_offset` |
| Prisoner suspension | `prisoner_suspension` |
| Drug-addiction suspension | `drug_addiction_suspension` |
| Foreign work | `foreign_work_deduction` |
| Penalty | `penalty_deduction` |
| Maritime tax | `maritime_deduction` |
| Missing election certificate | `election_certificate_suspension` |
| Concurrent number-holder reservations and age reductions | `deduction_age_work_interaction` |
| Combined maxima; multiple auxiliary records | Existing named refusals remain |

The computation first obtains the ordinary G maximum-adjusted rates and
Parisi deductees. For each non-deductee it removes permanent deductees and
same-household temporary deductees from the original-benefit denominator.
The numerator is the available maximum less the applicable deductees'
partial payables and age reductions. The resulting proportional share is
capped at the original benefit and dime-floored before age reduction. A
zero dual rate remains disregarded regardless of another deduction
(GN 02603.050A.2). Explicit dual markers must match the existing own-benefit
declaration and computed payable; they do not apply a second offset.
An `OWN_EARNINGS_TEST` event must withhold a strictly positive amount after
NH reservations. R2 selects events only where its actual own deduction is
positive, including when annual excess is zero. A zero-amount event is
therefore `InvalidFamilyInput` in both public G forms, before event coverage
refusals. It produces no result or denominator row and cannot freeze a
rate, release rounding slack or disable A.1's single-full-deduction rule.
Household and family coverage refusals are held until amount-dependent
input checks finish on every computable record. In the invented survivor
PIA $4/MAX $6 case, a shared child and a unique child each have OB/gross $3
on one record; the shared child also appears on a second record. A unique
child's zero-withholding $3 event is invalid before the household's combined
maximum refusal. The shared child's unsettled maximum cannot mask a
separately derivable input error.

`BeneficiaryBenefit.deduction` records the amount withheld from that row's
age-adjusted gross amount after its own-benefit offset, and
`deduction_reason` records the explicit event. For a number-holder partial
month, `reserved_work_deduction` preserves a non-deductee's prior NH charge
beside its resulting rate. R2 retains the NH amount in its ledger. Exact
partial payables and counted reserves can be fractions of a dime because
R2's pro-rata allocation precedes final whole-dollar check rounding. The
original and redistributed rates remain exact dime multiples. No-deduction
results have zero deduction and reserve fields.

Fixed dual and outside-maximum beneficiaries still bear their NH charges.
Their gross rates stay fixed; their exact `deduction` equals their
`reserved_work_deduction`, with no qualifying `deduction_reason`. The
sealed result permits this equality explicitly. Subject dual payables
reserve the amount remaining after NH charging, because the same NH amount
is already in the global reserve. Outside-maximum NH deductions never enter
that reserve. An outside-maximum own-work event likewise releases no
subject maximum room (403(a)(3)(C); GN 02603.040B; RS 02501.155B.3.c).

The R2 NH-reservation Hypothesis test covers two minimized counterexamples.
PIA $600/max $900, a spouse with own RIB $10 and two children gives ordinary
auxiliary rates $90/$105/$105. NH excess $600 leaves each auxiliary $60;
a child's own $30 deduction raises the other child to $90 and leaves the
spouse $60. A divorced spouse outside the maximum with three children has
ordinary rates $300/$100/$100/$100. NH excess $600 leaves each auxiliary
$100; one child's own $30 deduction leaves it $70 and raises the other
children to $115 each. The divorced spouse remains $100. Earlier draft
code refunded the fixed beneficiaries' NH charges and incorrectly included
the divorced spouse's NH charge in the subject pool. These were arithmetic
integration errors, not alternative statutory readings.

Executed invariants in `test_track_b_gross_benefits_deductions.py` are:

- `test_no_deductions_is_exact_family_and_household_differential`: exact
  equality to ordinary G for both public forms, including Parisi families.
- `test_formula_bounds_monotonicity_households_order_and_determinism`:
  non-deductee rates do not fall when the first own-earnings deduction is
  added in the generated unreduced survivor families; rates do not exceed original benefits,
  subject totals do not exceed the maximum, separate-household temporary
  rates equal their prior rates, permanent rates equal GN 02603.050C,
  determinism and order independence. Hypothesis varies PIA, family size,
  partial amount and permanence.
- `test_unsupported_deductions_keep_named_denominator`: every named event
  refusal remains in the denominator and invalid IDs are input errors.
- `test_fields_remain_sealed_and_exact`: fractional partial payables remain
  exact and results cannot be constructed through their public class.
- `test_nh_partial_reservation_cannot_redistribute_original_rounding_slack`:
  a partial NH month does not release the preexisting unused dime-rounding
  balance. RS 02501.155B.3.c permits only the auxiliary's actual deduction
  to increase the other auxiliaries' partial benefits.

GN 02603.060 A.1 produces $182.80 for each child after E's full deduction;
A.2 caps E and C1 at $225.30; B.1 leaves E $37.20 and each child $170.40.
C.1 leaves separate-household C1 $137.10 while C2 and C3 receive $182.80.
C.2 keeps the zero dual C2 rate, pays C3 $225.30 and initially pays C1
$182.80; permanence raises C1 to $225.30. Existing A.5, A.8, A.9 and B.2
Parisi cases enter unchanged through the new path. A.6 and A.7 require
combined family maxima and remain refused by the declared lane scope.
Workers' compensation examples A.3, A.4 and B.3 remain refused.

RS 02501.130's no-care months pay the children $83.50 each.
RS 02501.160's full month pays same-household C2 $132 while E and C1 remain
at $99; June's partial C3 payment of $39 gives C2 $119. At permanence E
and C1 receive the same $132 or $119 rates. The captures' original
benefits round upward: PIA $213.10 has quoted OB $159.90 and PIA $242.30 has
quoted spouse OB $121.20. G's post-1982 dime flooring instead yields
$159.80 and $121.10. Equal OB weights make every stated adjusted payment
identical; tests pin both quoted OBs and modern OBs rather than overriding
the arithmetic or claiming historical rounding coverage. The captures do
not date these examples or establish why they used upward rounding.

### Settled reading and deferred coverage

GN 02603.050D.2 says "there are no partial deductions for temporary work
deductions". RS 02501.160 Example 2 nevertheless instructs immediate
same-household redistribution in June with C3 $39 and C2 $119, while E and
C1 remain $99 until permanence. This implementation follows the explicit
payment example and the dispatch's authorization of estimated partial
amounts. The literal GN sentence would refuse that temporary partial case;
it would withhold C2's $20 June increase. The source assertions pin both
sentences. No switch invents a different benefit amount.

The interaction of NH reservations and age reductions is deferred coverage:
no allocation procedure has been derived for the combined configuration.
This is not a conflict between authoritative algorithms, and missing worked
examples alone do not establish an ambiguous reading. The implementation
refuses the mixed configuration as `deduction_age_work_interaction`.
No population processing, combined maximum determination,
multiple auxiliary-record selection or annual earnings determination is
in scope here.


## Operational saving clause, October 23, 2026

Verification class: statutory conformance on invented cases and captured
SSA rules. This extension admits no population, behavioral or forecast
claim. Max's d1338 selects SSA's operational interpretation of 203(a)(5)
(42 U.S.C. 403(a)(5)); d1802 authorizes its implementation here. This section
supersedes earlier descriptions of the default as a refusal.

### Declared interface and payment meaning

`SavingsClauseGuard(first_month, *, earlier_months_unknown,
reading=SavingsClauseReading.SSA_OPERATIONAL)` takes an exact `YearMonth`,
a built-in Boolean, and a canonical enum. Its read-only `reading` accessor
returns that enum. `LITERAL_REFUSAL` retains the G v2 behavior, and all
existing tests of that reading select it explicitly. `admit` returns a
sealed `FamilyBenefits`, including a protected result when needed;
`evaluate` returns that result in a sealed outcome. Validation happens once
at each public boundary; provenance and integrity checks do not claim
freshness or caller attribution.

`BeneficiaryBenefit.age_reduction_factor` retains the exact 402(q)
multiplier before money rounding (Fraction, zero through one).
`FamilyBenefits.worker_reduced_for_age` is a built-in Boolean derived from
the worker's declared reduction months; `worker_age_reduction_factor` stores
the exact Fraction multiplier and must agree with that flag. Rounded money cannot reconstruct
that factor or reliably identify an age reduction at very small amounts.
The established formula maximum, available room, proportional shares and
counted amounts do not change when the saving clause raises payment.
`age_adjusted_rate`, `auxiliary_payable`, and their exact and whole-dollar
totals contain the protected payment; the beneficiary note identifies it.
This implements RS 00630.400's statement: "The established FMAX will not
change—only total benefits payable are affected."

### Conditions and supported procedures

Under `SSA_OPERATIONAL`, the prior month must have two or more entitled
persons, a binding maximum, and at least one age-reduced beneficiary. The
next month's PIA must rise and its family total must fall. These are the
four requirements in RS 00630.400's "1972 Family Payment Saving Clause".
Membership and exact worker/auxiliary age factors must be unchanged for the
supported payment computation. The four source conditions are evaluated
before this coverage boundary. A qualifying PIA increase and fall with
changed membership refuses as `savings_clause_membership_change` and retains
uncertain history. A membership-only decline without a PIA increase starts
no protection.
A simultaneous change of age factors or a declining formula maximum with
a qualifying overall fall refuses by name because the snapshots do not
isolate the PIA effect. For example, PIA/FMAX $100/$150 with an unreduced
worker, a spouse reduced 36 months and two children pays $145.60. PIA/FMAX
$101/$140 pays $136.70, but the PIA increase alone with FMAX $150 pays
$145.80. The simultaneous maximum decline is therefore not admitted as a
PIA-caused loss.
A later departure without a PIA increase starts no
protection. The guard carries an established protected total under RS
00615.801B.2, also retaining it while the ordinary formula payment overtakes
it because the source says it may become payable again. A change of
entitled identities, roles, worker entitlement or record kind during that
carried protection refuses, including later months after the change.

| Configuration | Result |
|---|---|
| Life case, only the worker reduced for age, stable auxiliaries | Subtract the new worker rate from the protected family payment, divide by the number of auxiliaries and round to equal dime rates (RS 00630.400) |
| Life case, one reduced spouse and at least one other auxiliary | Divide the family-payment loss by the auxiliary count; apply the spouse's exact RF to that increase and add it to the spouse's ordinary reduced rate; divide the remaining protected amount after the new worker and spouse rates among the other auxiliaries (RS 00630.400) |
| No qualifying age reduction, no PIA increase, or no immediate fall | No operational protection starts |
| Later raw payment is below an established protection | Reapply the captured procedure without changing formula FMAX (RS 00615.801B.2) |
| Entitlement membership changes at the first qualifying fall or during carried protection | `savings_clause_membership_change`; the captured 1972 procedure does not establish successor protection |
| Survivor, own-benefit offset, deduction, multiple reduced auxiliaries, lone reduced spouse, simultaneous age-factor change or declining FMAX with a qualifying fall, or a protected rate above OB | `savings_clause_rate_procedure`; the captured life-case allocation does not settle these rates |
| Prior history is unknown or a skipped month may hide protection | `savings_clause_history_unknown`, retained in every denominator |
| Explicit literal alternative reaches any later lower governed total | Existing `savings_clause_403a5` refusal; the original broad interpretation remains testable |

### Invented worked calculations and source integrity

The capture contains a procedure, not worked dollar figures. These invented
calculations therefore make no claim that their figures are quoted SSA
examples. `test_operational_source_rules_are_quoted_from_captures` checks
every cited rule verbatim against the existing SHA-pinned RS 00630.400 and
RS 00615.801 captures; the original manifest test recomputes their SHA-256.

1. Only worker reduced: PIA $1,000, FMAX $1,500, worker reduced 60 months
   to $700, two children $250 each: $1,200 total. PIA rises to $1,010,
   FMAX unchanged, worker $707 and children $245: $1,197. Protection pays
   each child ($1,200 − $707)/2 = $246.50, restoring $1,200 exact and
   $1,199 after separate whole-dollar floors. Formula FMAX stays $1,500.
2. Worker and spouse reduced: the same initial worker and FMAX, spouse
   and two children receive $108.20, $166.60, $166.60: $1,141.40 total.
   PIA $1,010 yields worker $707, spouse $106.10, children $163.30 each:
   $1,139.70. Loss $1.70 divided by three rounds up to $0.60; the
   spouse's 65 percent factor gives $0.39, floored to $0.30. Spouse
   $106.40 leaves ($1,141.40 − $707 − $106.40)/2 = $164 per child.
   Exact and whole-dollar totals are $1,141.40 and $1,141.
3. Rounding boundary: first case with PIA rising to $1,001 gives worker
   $700.70. Equal protected children need $249.65 each; $249.70 each
   pays $1,200.10. Rounding each down to $249.60 instead pays $1,199.90.
   This ten-cent shortfall is the explicit reading question below.
4. The actual round-11 COLA witness is retained: survivor PIA $4.40,
   formula maximum $6.60, two unreduced widows $2.40 each and a
   mother/father $1.80, total $6.60. A 2.3 percent COLA yields PIA
   $4.50, maximum $6.70, and shares $2.40, $2.40, $1.70: $6.50.
   The operational age condition fails, so no protection starts; the
   explicit literal reading refuses. There is no assertion that a COLA
   alone cannot lower payment.

### Executed invariants

- Each reading starts on exactly its own declared conditions:
  `test_both_readings_start_exactly_on_their_conditions` (Hypothesis).
- Protected supported payment is at least the protected total; equal-dime
  rounding excess is strictly less than the number of remaining auxiliaries
  times one dime. Formula FMAX and counted subject total remain unchanged:
  the same property and the worker/spouse/rounding example tests. The
  deterministic property also checks every protected rate against OB; the
  carry property refuses a later lower PIA when its protected rate would
  exceed OB (203(a)(4); the capture does not settle above-OB payment).
- Allocation and protection are deterministic and independent of beneficiary
  order: `test_operational_is_deterministic_order_independent_and_sealed`
  (Hypothesis).
- Carried protection can become payable again:
  `test_operational_carries_and_can_become_payable_again` and Hypothesis
  `test_operational_carry_membership_refusal_and_denominator_properties`.
- Every named operational refusal preserves the full row and weight:
  `test_operational_named_refusals_stay_in_denominator` and the preceding
  Hypothesis carry/membership/denominator property.
- Membership-driven declines without PIA increases start no protection:
  `test_operational_child_departure_never_starts_without_pia_increase` and
  Hypothesis `test_membership_declines_without_pia_increases_never_start_protection`.
- Concurrent changes of exact worker or auxiliary age factors cannot be
  silently attributed to a PIA increase or silently treated as unprotected:
  Hypothesis `test_simultaneous_basis_change_refuses_ambiguous_fall`
  keeps each qualifying mixed-change fall as a named refusal. An improving
  worker factor is included: PIA $100/RF60 gives $120; PIA $102/RF59
  gives $119.80, even though changing RF alone raises payment to $120.40.
- Invalid enum values and forged protected outputs are input errors:
  `test_default_is_operational_and_literal_is_explicit` and
  `test_operational_worker_reduction_protects_payment_not_maximum`.
- The literal alternative retains the original paths and denominator rules
  in the pre-existing guard property suite, now explicitly selected.

### Reading taken: the direction of the operational rounding

This is the session's reading under Max's 2026-10-20 delegation, logged in
the source-conflict rulings as
`us:oasdi-saving-clause-operational-rate-rounding` (P1: the Act's "assure
... will not be less" fixes the direction the procedure leaves open).
The captured rate procedure says "Difference ÷ By the Number of Auxiliaries
(rounded) = Auxiliary Rate;" and "Difference ÷ the Number of Auxiliaries
Rounded = Increase." It does not state the direction. Act 203(a)(5) says
"smallest amount that would have been required in order to assure that
the total of monthly benefits payable on the basis of such wages and
self-employment income for any such subsequent month will not be less";
ordinary modern rates under RS 00615.201 round down. The implementation
uses the smallest equal dime rates that meet the protected total (round
up), while still flooring the spouse's age-reduced increase. The boundary
above changes total payment by $0.20 versus flooring equal child rates,
and prevents a $0.10 shortfall. `LITERAL_REFUSAL` is the conservative
alternative when a protected raise would be required. No rounding choice
is hidden; the example and mutation check pin it. A carried protection that
would require an auxiliary rate above OB refuses with
`savings_clause_rate_procedure`: 203(a)(4) describes decreases, while the
captured .400 procedure does not state its OB cap. The minimized executed
case has PIA/maximum $0.40/$0.60, then $0.50/$0.60, then $0.10/$0.10,
a worker reduced 60 months and two children. Before this check the final
children would each receive $0.20 despite dime-rounded OB $0; that is now
an explicit refusal, not an admitted above-OB interpretation.

RS 00615.801B.2 says "until the table or formula maximum becomes larger"
and immediately adds that "it is possible that the savings clause maximum
may again become payable". The guard retains its protected history through
an intervening larger ordinary payment and refuses membership changes
while that history is carried. This deliberately conservative membership
boundary may refuse a change during an otherwise dormant protection.
The invented case in
`test_operational_carry_membership_refusal_and_denominator_properties`
starts at PIA $1,000, maximum $1,500, a worker reduced for 60 months and
two children: January pays $1,200. February PIA $1,001 establishes the
$1,200 protected floor and pays $1,200.10 after rounding. March's maximum
$1,600 allows the ordinary $1,299.70, while the $1,200 floor and its
January origin remain recorded. Removing one child in April would allow
an ordinary $1,201.20, above that floor, but the dormant-history membership
boundary refuses it. Extinguishing the history in March would instead
admit that $1,201.20. The existing Hypothesis property executes this
boundary and preserves the refused row and weight in the denominator;
the source-quote test pins the complete "may again become payable" rule.

### Deduction history and protected payment totals

The saving-clause guard must inspect deduction metadata in both the current
and prior month. Deduction results retain a deductee's pre-offset
`age_adjusted_rate` while changing `auxiliary_payable` and other members'
maximum shares. Those rates therefore cannot establish an operational
family payment without an additional captured rule. Numeric `deduction`
and `reserved_work_deduction` count even when `deduction_reason` is absent
for an NH-only reservation. These fields remain part of each sealed result.
Subject own-benefit facts are likewise checked in both months before
establishing or extending protection, even while a carried floor is dormant.
An own benefit ceasing at the trigger cannot turn the prior pre-offset
diagnostic total into a payment floor. These unsettled procedures refuse
as `savings_clause_rate_procedure` and retain the uncertain history.

Executed counterexample: January PIA $1,000, FMAX $1,500, a worker reduced
60 months to $700, and two children. One child's full permanent own-work
deduction leaves the other child $500; actual record payment is $1,200.
The deductee retains a diagnostic $250 age rate, making the pre-offset
saving-clause total $1,450. With PIA $1,010 and no deduction in February,
ordinary payment is $1,197. A guard looking only at February's deduction
flags formerly raised that payment to the spurious $1,450 floor. Candidate
protections now refuse as `savings_clause_rate_procedure` if either month
has a subject deduction. An already carried protection also refuses that
interaction even when the diagnostic pre-offset total is above its floor.
The uncertain history is retained for later months. A month with no active
or candidate protection still returns its genuine result unchanged.

The existing Hypothesis
`test_operational_carry_membership_refusal_and_denominator_properties`
executes both historical and current-deduction controls, including this
$1,000 example. The gap belongs to RS 00630.400's uncaptured interaction
with GN 02603.050, not to input validity. No protected amount is inferred
from a diagnostic pre-offset total, and every refusal retains its row and
weight. Completing this combined payment procedure remains outside scope.

### Round-2 input and history regressions

The following are invented calculations, not published SSA examples.

| Inputs | Ordinary calculation and resulting boundary |
|---|---|
| January 2024 PIA $4/MAX $6, spouse reduced 60 months | Spouse $1.30, whole dollars $1; a no-care declaration is invalid and cannot replace this with $0 |
| Same record, plus two children and a full spouse own-work deduction | Children $1 each, whole dollars $1 each; a child event payable $.60 withholds zero and is invalid |
| PIA $48/MAX $78, spouse reduced 60 months and three children | A full spouse deduction leaves children $10 each; adding a child's zero-withholding $7.50 marker is invalid |
| Survivor PIA $1/MAX $1.10, three children | $.30 each and $.90 total; a $.30 own-work marker is invalid and cannot raise siblings to $.40 |
| PIA $.40/MAX $.60 rises to $.50 with unchanged MAX and worker RF60; children C0/C1 become C0/C2 | Ordinary totals $.40 then $.30; the qualifying membership change refuses, whereas stable membership protects $.50 |
| PIA $1,000/MAX $1,500 rises to $1,010, worker RF60 | January $1,200; replacement/removal gives ordinary $1,197 and addition $1,196.90; all qualifying membership changes refuse |
| Spouse or child own benefit $.10 ceases as PIA $1 rises to $1.10, MAX $1.50, worker RF60 | Prior actual total $1.20, pre-offset diagnostic $1.30; current ordinary $1.10 cannot establish a $1.30 floor and refuses |

The new files `test_track_b_gross_benefits_deductions_fix_round_2.py` and
`test_track_b_gross_benefits_savings_fix_round_2.py` execute these boundaries.
Every new invariant has a Hypothesis property beside the examples:

- `test_under_fra_attestation_cannot_admit_an_age_reduced_spouse` and
  `test_no_care_spouse_requires_unreduced_under_fra_attestation` enforce
  the spouse age exclusion and required eligibility fact in both public
  forms. `test_age_reduced_no_care_is_input_error_before_refusal` keeps
  invalid declarations out of the denominator even with a held refusal.
- `test_zero_event_cannot_change_existing_full_deduction_output` rejects
  permanent and temporary no-op events without any result or denominator
  change, preserving exact and whole-dollar controls, determinism and the
  existing full age-reduced deductee. R2's Hypothesis property
  `test_r2_emits_only_positive_actual_deduction_events` differentially
  checks every emitted final/provisional G event against actual deductions.
- `test_qualifying_membership_change_is_order_independent_refusal` keeps
  first-trigger membership changes in the weighted denominator and retains
  uncertain history independently of beneficiary order.
  `test_membership_decline_without_pia_increase_stays_admitted` preserves
  the supported no-PIA-increase control.
- `test_prior_own_benefit_cessation_always_preserves_uncertain_history`
  and `test_current_own_benefit_never_certifies_candidate_or_carried_protection`
  prohibit a diagnostic pre-offset own-benefit rate from establishing or
  extending protection, including dormant protection. Every legal refusal
  retains its full weight; input errors retain no denominator row.

These implement the orchestrator's settled readings under Max's
2026-10-20 delegation. First-trigger membership and prior-month own-benefit
cessation add deferred procedure coverage, with the named reasons above;
they do not assert an alternative supported payment algorithm. The existing
temporary-partial reading, least-sufficient-dime rounding, qualified
monotonicity, A.1 exception and deduction-history refusal remain in force.

### Not in scope

No combined family maximum, multiple auxiliary records, survivor allocation
extension, unknown-history reconstruction, population application or
empirical claim is added by this saving-clause implementation.

GN 02603.050A.1 expressly excepts a single full permanent deduction with
no other deduction: "disregard that beneficiary when distributing the
family maximum". Accordingly the implementation reserves no age reduction
for that one row. The invented regression
`test_single_full_permanent_exception_disregards_age_reduction` uses a
$400 PIA, $650 maximum and age-reduced spouse with two children. The children
receive $125 each. Blind application of C's age-reserve formula would retain
$20.90 and pay $114.50 each. This is an intended exception to the general
permanent-formula identity, rather than an alternate default interpretation.
The requested absolute non-deductee monotonicity invariant cannot hold
together with A.1 and C. A.1 says "and no other deduction is involved for
any beneficiary"; C includes "Age reduction amount for all workers or
deductees". Thus adding a second deductee ends the exception and restores
the first deductee's age reserve. The same test pins and property-tests
this intended discontinuity over integer scales 1 through 20. The
minimized invented case has PIA $48, maximum $78, a spouse reduced for 60
months and three children. Baseline child rates are $7.50 and the spouse's
age reserve is $2.70. A full permanent spouse deduction pays the children
$10 each. Adding a child's $0.10 own deduction leaves that child $7.40
and gives each other child floor(($30 − $2.70 − $7.40) / 2) = $9.90.
Extending the disregard despite the second deductee would instead pay
$11.30 each, but contradicts A.1's explicit no-other-deduction condition.
The $48 case was minimized on the original maximum/PIA ratio of 13/8,
with dime-aligned amounts and a $0.10 additional deduction, after reducing
the child count from five to three. This is a qualified invariant, not a
silently changed payment rule.
`test_all_dual_beneficiaries_do_not_gain_from_another_deduction` preserves
GN 02603.045's exclusion of dually entitled recipients from increases.

`test_impossible_payable_precedes_statutory_refusal` property-tests the
input-before-coverage invariant in both new public forms: a payable plus
number-holder reservation above the original benefit is invalid even when
the record carries an otherwise refused workers' compensation offset. Such
an input creates no denominator row. Exact post-reduction bounds are checked
when the ordinary G computation admits that configuration.

GN 02603.060 A.2's narrative says "That is $548.40 divided by 2
individuals = 225.30." Its displayed formula correctly gives $274.20
before the original-benefit cap of $225.30. The existing A.2 test pins the
literal narrative, raw quotient and capped payment side by side. This is
an omitted cap in the narrative, not an alternate arithmetic rule.
