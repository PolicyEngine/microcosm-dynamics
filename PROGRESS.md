# Official PSID inventory registries progress

## State

Blocked before either official registry blob. The exact section 4.2 schemas
have no unresolved/registration-required row disposition, and the registered
authorities do not yet determine the complete questionnaire-slot domain or the
fixed-width parse grammar needed for a truthful source-field inventory.

No `psid_questionnaire_slot_specs.v1` or
`psid_covered_earnings_source_field_inventory.v1` artifact has been emitted.
An empty, partial, reader-derived, or inferred artifact would violate the
design's completeness, ordering, foreign-key, and fail-closed laws.

## Done

- Confirmed the requested branch and baseline commit `13f84c99` and read the
  prior regs1 report, section 4.2, and the section 16/17 extensions.
- Verified all 456 registered corpus documents are present and match the
  accepted authority registry. The 43 family questionnaires cover interview
  waves 1968 through 2023 and comprise 5,692 pages.
- Audited the 32 codebook-adjudication residuals against the committed #345
  registration, extraction, closure, and Amendment-3 projections. Exactly 7
  are resolved and 25 survive.
- Partitioned the 25 survivors by consequence: 7 block the slot registry, 6
  additional fixed-width grammar residuals block the source inventory, and 12
  are downstream allocation/reconciliation/job-attachment residuals.
- Confirmed #345's semantic extraction did not target any of the 7 complete
  slot-taxonomy/absence residuals. Corpus registration proves byte identity,
  not a source-derived job/component taxonomy or exhaustive absence proof.
- Confirmed only 43 waves, 2 roles, and 35 purposes are presently exact. The
  job-slot and questionnaire-component dimensions are not established, so an
  exact `expanded_slot_count` (and therefore inventory `row_count`) cannot be
  computed.
- Confirmed the local #348 repin changes only the revision-5 design binding;
  it adds no registry authority, artifact, builder, or test.
- Ran the pinned authority/registry verification set: 282 tests passed.
- Ran the complete focused PSID inventory/corpus suite: 182 tests passed.
- Verified the collection-wide tier policy (1 passed, 4,470 deselected), the
  unchanged 4,471-test collection, and all Ruff checks.
- Wrote the complete law, authority, residual, critical-slot, test, and
  ratification-path report to `e11-inventory-final-report.md`.

## Next

- Perform and separately review an exhaustive source-only semantic extraction
  of all 43 questionnaire flows, with the complete job/component taxonomy,
  exact positive locators, and exhaustive negative-domain proofs.
- Obtain source-backed fixed-width padding/sign/blank/sentinel grammar for all
  six adjudication eras.
- Only then render, validate, and separately ratify the complete slot registry;
  render the positionally identical source inventory from that immutable blob.
- Preserve the 12 downstream semantic residuals for their separately reviewed
  rule registries/crosswalk rather than folding them into source facts.
