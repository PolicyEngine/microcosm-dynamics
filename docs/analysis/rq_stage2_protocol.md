# R_Q stage-2 per-document annotation protocol

## Status and scope

This is a nonauthority lane protocol for the 81 source-only document shards
described in section 19. It does not define a substitute Q5 schema, close a
Class-A or Class-B residual, or authorize a passing canonical era row. Section
19 defines no accepted per-document authority schema. Each lane seals exactly
one independently replayed `questionnaire_flow` document and hands its rows to
the later global catalog, alias, and `R_Q` assembly.

The lane must not read a slot, inventory, crosswalk, reader, legal-registry, or
desired-classification candidate. It must not assign final global role, job,
component, alias, or relationship IDs. Cross-document equivalence and all
global catalogs remain unresolved until the complete document domain has been
concatenated in source order.

The controlling laws are section 19's source projection and candidate
nonselection law, page and occurrence law, flow law, catalog and alias law,
whole-document locator law, and build order. The committed stage-1 replay and
candidate index are fixed inputs:

- `docs/analysis/rq_stage1_evidence/source_replay_v1.json` fixes the
  independently authenticated document and page denominator.
- `docs/analysis/rq_stage1_candidates/index_v1.json` identifies the one
  candidate artifact and manifest for the document.
- Candidate artifacts are machine review aids only. They cannot select a
  source, occurrence, path, classification, alias, or output row.

## Candidate adjudication contract

Before sealing a document, exact-disposition the locator candidate, every
candidate page row, every occurrence candidate, every flow-path candidate,
and every anchor-classification candidate exactly once. A lane-local candidate
disposition row has exactly:

```text
candidate_row_kind
candidate_id
disposition
stage2_row_ids
adjudication_status
```

`candidate_row_kind` is exactly `whole_document_locator | page | occurrence |
flow_path | anchor_classification`. `disposition` is exactly `accepted |
modified | split | rejected`. An accepted or modified candidate names exactly
one output row, a split candidate names at least two, and a rejected candidate
names none. `adjudication_status` is `complete`. Candidate IDs remain in this
provenance relation and never become final-form row IDs.

Every stage-2 output row has exactly one lane-local adjudication row with these
members:

```text
stage2_row_kind
stage2_row_id
source_candidate_ids
adjudication_action
whole_page_review_complete
source_span_verified
adjudication_status
```

`source_candidate_ids` is the complete ordered input projection.
`adjudication_action` is exactly `candidate_accepted | candidate_modified |
candidate_split | manual_add`. A manual addition is lawful only after the
entire source page has been reviewed; it has `source_candidate_ids: []`,
`whole_page_review_complete: true`, `source_span_verified: true`, and a
strictly re-sliced source span. All rows have `adjudication_status: complete`.
The two adjudication relations must agree in both directions.

No candidate auto-promotes. Every output is an explicit reviewer decision,
including an output that happens to equal a candidate. A page with zero
candidates does not prove that the canonical occurrence set is empty. An
unreviewed page, candidate, or output row blocks the document seal.

## Whole-document locator

The shard has exactly one locator row with exactly these 11 members, in this
displayed order:

```text
locator_id
source_document_id
interview_wave
filename
location_type
byte_start
byte_end
size_bytes
full_file_sha256
range_sha256
pdf_page_domain
```

It resolves the independently replayed document, singleton wave, canonical
source-path basename, complete regular-file bytes, size, and SHA-256. It obeys
all five equations:

```text
location_type == whole_document_exact_file_range
byte_start == 0
byte_end == size_bytes
range_sha256 == full_file_sha256
pdf_page_domain == all_pages_and_flow_branches
```

`locator_id` is `psid-whole-document:` followed by the SHA-256 of terminal-LF
canonical JSON bytes of:

```text
[source_document_id, interview_wave, full_file_sha256, size_bytes]
```

A page range, search hit, snippet, filename-only match, or same-title file is
not a lawful locator.

## Complete page cover

Each page row has exactly these eight members, in this displayed order:

```text
questionnaire_page_id
source_document_id
source_locator_id
interview_wave
page_number
page_text_utf8_sha256
questionnaire_occurrence_ids
annotation_status
```

Rows exact-cover every page emitted by the pinned Poppler derivation,
including pages with an empty occurrence array. They follow page-number order.
`page_number` is a positive integer excluding booleans. Document, wave, and
locator resolve the shard; the text digest hashes the complete exact UTF-8
page bytes; `questionnaire_occurrence_ids` is the complete same-page
source-order projection; and `annotation_status` is `complete`.

`questionnaire_page_id` is `psid-questionnaire-page:` followed by the SHA-256
of terminal-LF canonical JSON bytes of:

```text
[source_document_id, interview_wave, page_number, page_text_utf8_sha256]
```

Document/page coordinates and IDs are unique. Page count, ordered row domain,
and all page hashes must reproduce the stage-1 replay independently of the
candidate artifact.

## Exact occurrences

Each occurrence row has exactly these 14 members, in this displayed order:

```text
questionnaire_occurrence_id
source_document_id
source_locator_id
source_locator_sha256
interview_wave
page_number
utf8_byte_start
utf8_byte_end
occurrence_index_on_page
semantic_ordinal_at_span
occurrence_kind
matched_text
matched_utf8_sha256
flow_branch_paths
```

`occurrence_kind` is exactly one of these ten values, in this order:

```text
flow_branch_label
role_anchor
job_anchor
remuneration_component_anchor
role_total_anchor
farm_aggregate_anchor
business_aggregate_anchor
context_anchor
field_purpose_prompt
repeat_or_alias_instruction
```

Offsets are nonnegative half-open UTF-8 byte offsets aligned to character
boundaries in the exact page bytes, with `utf8_byte_start < utf8_byte_end`.
`matched_text` is the strict-decoded, nonempty exact slice without
normalization, and `matched_utf8_sha256` hashes those exact bytes. Document,
locator, wave, and page deep-equal the containing page row.

Within a page, rows are ordered by `(utf8_byte_start, utf8_byte_end, displayed
occurrence-kind order, semantic_ordinal_at_span)`. `occurrence_index_on_page`
is the zero-based position in that complete order. Except for a multi-parent
`flow_branch_label`, at most one atomic occurrence may share a span and kind,
and its semantic ordinal is zero. A multi-parent label emits one same-span
occurrence per complete parent path in branch-path order; its ordinal is that
parent path's zero-based position. Any later fact supported by an existing
atomic occurrence reuses its ID.

`source_locator_sha256` hashes terminal-LF canonical JSON bytes of:

```text
[
  source_document_id,
  canonical_source_path,
  "questionnaire_page_utf8_span",
  [
    interview_wave,
    page_number,
    utf8_byte_start,
    utf8_byte_end,
    occurrence_index_on_page,
    semantic_ordinal_at_span,
    occurrence_kind
  ]
]
```

`questionnaire_occurrence_id` is `psid-questionnaire-occurrence:` followed
by the SHA-256 of terminal-LF canonical JSON bytes of the remaining 13 row
values in their displayed order. Every occurrence ID appears exactly once in
its containing page. IDs, locator digests, and full
`(document, page, start, end, kind, semantic ordinal)` coordinates are unique.

## Flow paths and branches

`flow_branch_paths` is a nonempty ordered array of nonempty branch-ID arrays.
Unconditional text has exactly `[["questionnaire-flow:root"]]`. A conditional
occurrence has every complete applicable resolving root-to-leaf path. A
branch-label occurrence carries exactly one complete parent path; its branch
row appends the new branch ID.

Branch paths are compared elementwise by unsigned UTF-8 bytes. When one path
is a proper prefix of another, the shorter path sorts first. This is the only
path ordering law.

Each branch row has exactly these ten members, in this displayed order:

```text
flow_branch_id
parent_flow_branch_id
source_occurrence_id
branch_path
interview_wave
source_locator_id
page_number
occurrence_index_on_page
branch_label
branch_label_sha256
```

The source occurrence resolves a `flow_branch_label`; locator, wave, page,
same-page index, exact matched label, and label digest deep-equal it. Parent is
`questionnaire-flow:root` or an earlier resolving branch in the same wave.
`flow_branch_id` is `questionnaire-flow:` followed by the SHA-256 of
terminal-LF canonical JSON bytes of:

```text
[parent_flow_branch_id, interview_wave, source_occurrence_id]
```

`branch_path` is the source occurrence's one parent path followed by the new
branch ID. Rows follow source-occurrence order. Branch IDs and source
occurrences are one-to-one. Reject a missing or multiple parent path,
unresolved or cross-wave parent, later parent, duplicate label row, duplicate
path, path outside the resolved wave domain, cycle, omitted label, or
unlocatable label.

For a finite nonempty same-wave occurrence set, branch compatibility is true
if and only if some resolved path in that wave has at least one path of every
occurrence as a prefix. The result is only that Boolean existence result. A
witness path is never selected or serialized.

## Document-local anchors and repeat evidence

Record provisional document-local classifications and their exact occurrence
evidence. These rows are lane handoff material, not a section-19 canonical
local-classification schema. Preserve exact printed identifiers, labels,
spans, and occurrence IDs. Do not fold case, normalize whitespace or
punctuation, stem, infer synonyms, infer from source order, or infer
`first_job == job_1`.

The only eventual alias relations are:

```text
explicit_repeat_instruction
explicit_cross_reference
same_printed_identifier_and_exact_label
```

Alias evidence contains the alias anchor, canonical anchor, and complete
source-order set of repeat or cross-reference occurrences on which the
relation depends. Every `repeat_or_alias_instruction` occurrence must be
explicitly dispositioned and handed off for later global consumption. A
cross-document target stays unresolved in the document shard; it cannot be
silently bound locally. No final `psid-job-slot:`, `psid-component-slot:`,
`psid-node-alias:`, or `psid-questionnaire-relationship:` ID is emitted.

## Per-document commit checklist

One document and only one document is sealed by each annotation commit. The
commit is ready only when every item below passes.

- [ ] The source-replay artifact and global candidate index reproduce their
  pinned raw and content SHA-256 identities before the document is selected.
- [ ] The shard's source position, document ID, wave, canonical path, file
  size, file digest, Poppler authority, page count, and page hashes deep-equal
  the independently replayed source rows.
- [ ] The one whole-file locator has the exact 11-key schema, ID preimage, and
  five whole-file equations above.
- [ ] Page rows have the exact eight-key schema and exact-cover every replayed
  page in page-number order, including every empty-occurrence page.
- [ ] The reviewer completed a whole-page pass for every page; zero machine
  candidates was never treated as absence proof.
- [ ] Occurrence rows have the exact 14-key schema, only the ten ordered kinds,
  strict source slices, correct hashes, exact ordering, zero-based indices,
  lawful semantic ordinals, unique coordinates, and recomputed IDs.
- [ ] Every page's occurrence-ID array is the complete same-page source-order
  projection and every occurrence resolves exactly once through its page and
  whole-document locator.
- [ ] Every unconditional and conditional occurrence carries the complete
  lawful path set in exact path order; no candidate alternative selected a
  subset.
- [ ] Branch rows have the exact ten-key schema, follow occurrence order, and
  pass earlier-parent, same-wave, ID, path-extension, one-label-to-one-row,
  uniqueness, resolution, and cycle rejection.
- [ ] Compatibility tests use only the existential prefix law and serialize no
  witness path.
- [ ] Local anchor classifications retain exact source evidence, assign no
  global node or relationship IDs, and introduce no normalized or inferred
  equivalence.
- [ ] Every repeat or alias instruction is explicitly dispositioned with its
  complete evidence; unresolved cross-document work is preserved for global
  assembly.
- [ ] The candidate disposition relation exact-covers the locator, page,
  occurrence, flow-path, and anchor-classification candidate domains exactly
  once as accepted, modified, split, or rejected.
- [ ] The output adjudication relation exact-covers every emitted row; every
  manual addition has an empty candidate projection, completed whole-page
  review, and independently verified source span.
- [ ] Counts, ordered keysets, row domains, candidate-disposition domains, and
  output-adjudication domains reproduce their sealed digests.
- [ ] Mutation tests reject a missing or reordered page, bad span/hash/ID,
  illegal ordinal or duplicate atom, unresolved/later/cyclic branch,
  omitted/duplicate label, selected path subset, inferred alias, omitted
  candidate disposition, and unadjudicated output.
- [ ] The shard states nonauthority status and emits no Q5, era seal, global
  catalog, global alias, `R_Q`, hierarchy, slot, inventory, or legal-registry
  artifact.

Any unresolved source interpretation or adjudication blocks the document
seal; it is recorded for review rather than replaced by a candidate choice.

## Amendment 1: Raster-visible branch labels absent from extraction

1. **Closed raster-only disposition.** This rule narrowly refines only the
   `unlocatable label` rejection under **Flow paths and branches** and the
   corresponding unresolved-source seal abort. A required printed branch-label
   instance MAY be dispositioned `raster_visible_text_absent` only when a
   whole-page review confirms both that the label is unambiguously visible in
   the pinned source page raster and that no exact label bytes are locatable in
   the exact pinned Poppler UTF-8 page text. Candidate or search-result absence
   alone is insufficient. A label represented by partial or garbled authority
   text is not absent and remains under the original abort. An ambiguous raster
   reading, any other unresolved source interpretation or adjudication, or any
   other checklist failure also continues to abort the seal.

   `raster_visible_text_absent` is a separate exception disposition. It does
   not extend the candidate `disposition` enum and is not a `manual_add`. Each
   exception record has exactly these members, in this displayed order:

   ```text
   disposition
   source_document_id
   questionnaire_page_id
   interview_wave
   page_number
   page_text_utf8_sha256
   exception_index_on_page
   visible_label_description
   approximate_raster_location
   authority_text_statement
   ```

   `disposition` is `raster_visible_text_absent` and
   `authority_text_statement` is
   `no_label_level_span_or_hash_emitted`. Document, wave, page, page identity,
   and page-text hash deep-equal the sealed page row. The nonnegative
   `exception_index_on_page` is the zero-based position in the reviewer's
   complete raster-source-order enumeration for that page. Exception records
   follow page-number and then exception-index order; the pair
   `(questionnaire_page_id, exception_index_on_page)` is unique. The visible
   label description is human-readable, and the approximate raster location
   distinguishes the printed instance. The page-text hash binds the
   complete-review absence finding to the pinned authority bytes.

   Each record must state that **no label-level UTF-8 span or label-level hash
   is emitted for this branch**. The exception emits no `matched_text`,
   `matched_utf8_sha256`, `utf8_byte_start`, `utf8_byte_end`, questionnaire
   occurrence ID, `source_locator_sha256`, `branch_label_sha256`, flow-branch
   ID, parent, or path, and it creates no occurrence row or branch row. The
   description, location, and exception index are diagnostic nonauthority
   metadata only. They must not become branch-label text, a source slice,
   semantic evidence, or input to an occurrence, branch, relationship, or
   other authority ID. Covering their bytes with the metadata integrity digest
   does not promote them to text authority. The pinned Poppler extraction
   remains the sole text authority: no OCR output, manual transcription,
   normalization, or neighboring text enters the authority chain as a
   substitute label.

2. **Fail-closed path consequence.** This is not a second exception or
   disposition. It is the necessary fail-closed consequence of rule 1 for an
   otherwise locatable source atom whose complete raster applicability crosses
   one or more rule-1 exceptions, and it narrowly refines the complete path-set
   and selected-path-subset checks. The lane must never re-root such an atom,
   treat it as unconditional, invent a parent or path, or serialize a path
   containing an exception key. It records the atom in the raster-only census
   with exactly these members, in this displayed order:

   ```text
   reason
   source_document_id
   questionnaire_page_id
   interview_wave
   page_number
   page_text_utf8_sha256
   utf8_byte_start
   utf8_byte_end
   occurrence_kind
   matched_text
   matched_utf8_sha256
   blocking_exception_keys
   emitted_questionnaire_occurrence_ids
   path_consequence
   ```

   `reason` is `raster_visible_text_absent`. The page fields deep-equal
   the sealed page row; the offsets, text, and text hash are the exact strict
   slice from the pinned page text; and `occurrence_kind` is one of the ten
   existing kinds. `blocking_exception_keys` is the nonempty unique array of
   `[questionnaire_page_id, exception_index_on_page]` pairs that block
   raster-complete paths. Every key resolves exactly one rule-1 exception in
   the same census, and keys follow that exception domain's page-number and
   exception-index order. The key
   `(questionnaire_page_id, utf8_byte_start, utf8_byte_end, occurrence_kind)`
   is unique. Records follow page number and the existing within-page source
   order, without creating a semantic ordinal or occurrence ID of their own.

   If at least one complete path resolves entirely through emitted extraction-
   authority branch rows, `emitted_questionnaire_occurrence_ids` is the
   complete source-order projection of the ordinary occurrence rows emitted at
   that source atom for the recorded kind and `path_consequence` is
   `emitted_with_all_resolving_extraction_authority_paths`. Those occurrence
   rows contain every such resolving path and no other path. If no complete
   extraction-authority path resolves, the ID array is empty,
   `path_consequence` is
   `withheld_no_resolving_extraction_authority_path`, and the atom emits no
   ordinary occurrence, branch, local anchor or field-purpose classification,
   or local repeat/alias evidence row. An exact-censused empty-ID record with
   this withheld consequence is the sole exemption from ordinary occurrence,
   branch, and local-evidence exact-cover and `omitted label` rejection for that
   source atom. Omitting the metadata record reactivates those aborts.
   Candidate rows remain exact-dispositioned under the existing enum; a
   candidate whose only possible output is withheld has `disposition` set to
   `rejected` and `stage2_row_ids` set to `[]`, while the sealed rule-2 record
   supplies the reason. A dependency link may only remove or qualify output. It
   never supplies positive branch, path, parent, compatibility, or semantic
   evidence. If the dependency or the complete extraction-authority path set
   is ambiguous, the original abort still applies.

3. **Raster-only incompleteness census.** A document that uses the rule-1
   disposition must carry a seal-local census that exact-covers every
   `raster_visible_text_absent` branch instance once and every rule-2 dependent
   extracted atom once. The census states total branch-exception count `N`,
   total dependent-atom count `M`, and per-page enumerations and counts for
   both domains. Branch per-page counts sum to `N`; dependent-atom per-page
   counts sum to `M`. `N` counts branch instances, not pages or distinct
   descriptions, and `M` does not change the branch-exception seal claim. A
   missing, duplicate, or inconsistent entry reactivates the applicable
   unlocatable-label or path-completeness abort.

   The exception records and census are sealed handoff metadata, not stage-2
   output rows, and remain outside both candidate and output adjudication
   relations. Rule-2 consequence records are also outside those relations, but
   any ordinary occurrence IDs they name remain subject to normal output
   adjudication. Both canonical ordered metadata domains, their page counts,
   `N`, `M`, the affected seal claim, reasons, and consequence statement must
   be covered by the artifact integrity and seal digests. Mutation checks must
   reject omission, duplication, reordering, page-identity or page-hash
   mismatch, bad exact slices or dependency keys, incomplete emitted-ID
   projection, count or claim mismatch, re-rooting, and reason or consequence
   drift.

   The census must include this consequence: every enumerated branch is handed
   off to later global assembly and enters the global catalog as a **CLOSED
   GAP** with reason `raster_visible_text_absent`; it is never silently omitted.
   Every dependent atom is handed off with the same reason and its recorded
   emitted-or-withheld consequence; it never silently enters a missing branch
   or disappears from the incompleteness account.
   `CLOSED GAP` closes the audit disposition, not the missing branch's
   semantics. The census is document-local handoff evidence and does not itself
   emit a global catalog row or final global ID.

4. **Affected-document seal claim.** Only a document with `N > 0` uses the exact
   claim template below, replacing `N` with the census total:

   ```text
   complete-under-extraction-authority with N raster-only exceptions
   ```

   This is a document-level claim; it does not relabel page rows or convert
   missing labels into complete occurrence or branch rows. It claims
   completeness under the pinned text authority subject to the enumerated
   exceptions, not complete raster-flow recovery.

5. **Fail-closed global consumption.** Q5 and every downstream global-catalog
   consumer must treat each such CLOSED GAP as absent-with-reason, never as a
   present or resolved branch, and must preserve the
   `raster_visible_text_absent` reason. A consumer must not infer or synthesize
   a label, span, hash, occurrence, branch ID, parent, path, compatibility,
   root or unconditional status, or semantics from the raster description,
   OCR, nearby extracted text, or another branch. If an output requires the
   branch to be present or flow coverage to be exhaustive, the consumer must
   fail or withhold that output rather than defaulting the branch, narrowing
   the denominator, or treating the gap as compatible evidence. An emitted
   rule-2 occurrence applies only on its serialized extraction-authority paths;
   a consumer must not extend it across a blocking exception. A withheld atom
   remains absent-with-reason and cannot create a global node or relationship.

6. **Invariance.** This amendment is purely additive. The 74 clean seals remain
   valid unchanged. A seal with zero raster-only exceptions retains its
   existing structure, status, bytes, IDs, hashes, and digests; it requires no
   empty census, reseal, or claim change. Existing page, occurrence, branch,
   candidate-adjudication, and manual-add schemas remain unchanged, as do every
   rule and abort not narrowly refined by rules 1 and 2.

## Amendment 1, correction 1: Per-instance attribution and sealed sidecar

This correction is append-only. The six rules below are the complete
controlling replacement for Amendment 1's six rules above. They supersede the
earlier Amendment 1 text wherever the two conflict, while leaving every
pre-Amendment-1 protocol byte and section 19 unchanged.

1. **Closed per-instance raster-only disposition.** This rule narrowly refines
   only the `unlocatable label` rejection under **Flow paths and branches** and
   the corresponding unresolved-source seal abort. A required printed
   branch-label instance MUST be dispositioned
   `raster_visible_text_absent` if and only if a whole-page review proves both
   that the specific instance is unambiguously visible in the pinned source
   page raster and that no nonempty exact span of the pinned Poppler UTF-8 page
   text is attributable to that same printed instance.

   A span is **attributable** only when whole-page raster and pinned-text
   review uniquely associates that exact byte interval with the specific
   printed occurrence. Page-wide byte equality is not attribution. Identical
   or similar bytes attributable to a different printed occurrence MUST NOT
   be reused. For example, q79 page 12 prints `1. YES` and `5. NO` at both C32
   and C38. The pinned spans for C32 are attributable only to C32. They neither
   supply authority for nor defeat the two C38 exceptions, because no exact
   pinned span is attributable to either C38 label instance.

   If a nonempty exact pinned span is attributable but is partial or garbled,
   the source atom MUST instead be treated as an ordinary occurrence. Its
   `matched_text`, offsets, and hash are the exact pinned bytes as they are;
   they are never a transcription or visual repair. A visual-fidelity
   observation MAY appear only in a nonauthority diagnostic correction note
   and MUST NOT alter the ordinary occurrence or become semantic evidence.
   Rule 2 may subsequently restrict or withhold that ordinary atom solely
   because of its complete path consequence. Candidate absence, search-result
   absence, or the existence of cleaner bytes elsewhere on the page is
   insufficient for either outcome.

   There is no discretionary arm. When the exception predicate is proved, the
   exception disposition is mandatory. When same-instance attribution is
   proved, ordinary exact-byte treatment is mandatory. If the raster reading,
   same-instance attribution, or either proof is ambiguous, or if any other
   source interpretation, adjudication, or checklist item remains unresolved,
   the original abort is the only alternative.

   `raster_visible_text_absent` is a separate exception disposition. It does
   not extend the candidate `disposition` enum and is not a `manual_add`. Each
   exception record has exactly these members, in this displayed order:

   ```text
   disposition
   source_document_id
   questionnaire_page_id
   interview_wave
   page_number
   page_text_utf8_sha256
   exception_index_on_page
   visible_label_description
   approximate_raster_location
   authority_text_statement
   ```

   `disposition` is `raster_visible_text_absent` and
   `authority_text_statement` is
   `no_label_level_span_or_hash_emitted`. Document, wave, page, page identity,
   and page-text hash deep-equal the sealed page row. The nonnegative
   `exception_index_on_page` is the zero-based position among the complete
   rule-1 exception domain for that page in raster source order. Exception
   records follow page number and then exception index; the pair
   `(questionnaire_page_id, exception_index_on_page)` is unique. The visible
   description is human-readable, and the approximate location distinguishes
   the specific printed instance. Both are diagnostic nonauthority metadata.

   Each record states that no label-level UTF-8 span or label-level hash is
   emitted for that branch. It emits no `matched_text`,
   `matched_utf8_sha256`, offsets, questionnaire occurrence ID,
   `source_locator_sha256`, `branch_label_sha256`, flow-branch ID, parent, or
   path, and it creates no occurrence or branch row. No exception record
   member, value, byte, key, index, count, order, or digest may become label
   text, a source slice, semantic evidence, or an input to an occurrence,
   branch, relationship, alias, authority ID, or other authority preimage.
   Sealing the exception metadata does not promote it to text authority. The
   pinned Poppler extraction remains the sole text authority: OCR, manual
   transcription, normalization, neighboring text, and another printed
   occurrence never substitute for the missing label.

2. **Deterministic fail-closed path consequence.** This is not a second
   exception or disposition. It is the necessary consequence of rule 1 for an
   otherwise attributable extracted atom whose complete raster applicability
   crosses one or more rule-1 exceptions. It narrowly refines the complete
   path-set, selected-path-subset, occurrence-index, and semantic-ordinal
   checks. The lane MUST NOT re-root the atom, treat it as unconditional,
   invent a parent or path, or serialize a path containing an exception key.
   It records the atom in the sidecar with exactly these members, in this
   displayed order:

   ```text
   reason
   source_document_id
   questionnaire_page_id
   interview_wave
   page_number
   page_text_utf8_sha256
   utf8_byte_start
   utf8_byte_end
   occurrence_kind
   matched_text
   matched_utf8_sha256
   blocking_exception_keys
   emitted_questionnaire_occurrence_ids
   path_consequence
   ```

   `reason` is `raster_visible_text_absent`. The page fields deep-equal the
   sealed page row. Offsets, text, and text hash are the exact strict slice
   from pinned page text, and `occurrence_kind` is one of the ten existing
   kinds. The key
   `(questionnaire_page_id, utf8_byte_start, utf8_byte_end, occurrence_kind)`
   is unique. Records follow page number and existing within-page source
   order; they mint no semantic ordinal, occurrence ID, or authority row.

   A complete path resolves if and only if its first member is exactly the
   `questionnaire-flow:root` sentinel and every following member, if any,
   resolves in order to an emitted extraction-authority branch row whose
   parent is the preceding member. The root sentinel is not an emitted row.
   Thus a root-only path resolves, and any longer resolving path is the root
   sentinel followed only by emitted branch rows.

   Let `B(a)` be every raster-applicable complete path of atom `a` that does
   not resolve solely because it traverses one or more enumerated rule-1
   exceptions. `blocking_exception_keys` MUST deep-equal the complete
   duplicate-free all-and-only union of every exception traversed by every
   path in `B(a)`, ordered by the global exception-record domain's page number
   and exception index. Each key is exactly
   `[questionnaire_page_id, exception_index_on_page]` and resolves exactly one
   rule-1 record in the same sidecar. No blocking key may be omitted, added,
   duplicated, or reordered. If any nonresolving applicable path has a cause
   other than an enumerated rule-1 exception, or if the dependency or complete
   path set is ambiguous, the original abort applies.

   Before blocked paths are filtered, the lane freezes each ordinary atom's
   `semantic_ordinal_at_span` from the original complete raster-applicable
   parent-path order. It freezes `occurrence_index_on_page` from the complete
   pre-filter occurrence-row numbering domain ordered by the existing
   `(utf8_byte_start, utf8_byte_end, displayed occurrence-kind order,
   semantic_ordinal_at_span)` tuple: one position for each non-multi-parent
   atom and one position for each complete-parent-path ordinal of a
   multi-parent `flow_branch_label`, including positions later withheld.
   Every emitted survivor retains those original values; neither value is
   densely recomputed after path removal or atom withholding. Thus indices in
   an affected emitted domain may be sparse.

   These positions and ordinals are fixed before the sidecar is constructed
   and are never computed from an exception or census field, key, count, byte,
   order, or digest. Blocked-path filtering therefore MUST NOT change any
   surviving row's `semantic_ordinal_at_span`, `occurrence_index_on_page`, or
   any ID-preimage component derived from those values. A surviving
   `flow_branch_label` row retains its original one parent path, ordinal, and
   index, so its `source_locator_sha256`, questionnaire occurrence ID, and
   flow-branch ID remain stable when other complete parent paths are removed.
   A non-flow occurrence continues to derive its questionnaire occurrence ID
   from its exact emitted `flow_branch_paths` under the existing 13-value
   preimage law; no counterfactual ID equality is claimed for a path set
   containing an un-emitted exception. A dense-renumbering mutation MUST be
   rejected.

   If at least one complete path resolves, the
   `emitted_questionnaire_occurrence_ids` array is the complete source-order
   projection of ordinary occurrence rows emitted at that atom for the
   recorded kind, and `path_consequence` is
   `emitted_with_all_resolving_extraction_authority_paths`. Those rows contain
   every resolving path and no blocked or other path. If no complete path
   resolves, the ID array is empty, `path_consequence` is
   `withheld_no_resolving_extraction_authority_path`, and the atom emits no
   ordinary occurrence, branch, local anchor or field-purpose classification,
   or local repeat/alias evidence row.

   An exact-censused empty-ID consequence record is the sole exemption from
   ordinary occurrence, branch, and local-evidence exact cover and the
   `omitted label` rejection for that source atom. Omitting the consequence
   record reactivates those aborts. Candidate rows remain exact-dispositioned
   under the existing enum; a candidate whose only possible output is withheld
   is `rejected` with `stage2_row_ids: []`. A dependency link only removes or
   qualifies output. It supplies no positive branch, path, parent,
   compatibility, or semantic evidence.

   Mutation coverage MUST include an omitted-key mutation that leaves a
   nonempty `blocking_exception_keys` array and recomputes every count, domain
   digest, sidecar digest, seal digest, and artifact digest. The validator MUST
   still reject it. In particular, removing either of q72 H7's two blocking
   H6 keys while retaining the other is an omitted-key failure, not a lawful
   nonempty union.

3. **Exact sealed nonauthority sidecar.** An affected artifact has exactly one
   outer member named `raster_only_incompleteness_census`. In the artifact's
   displayed outer schema it appears immediately after `correction_note_rows`
   and immediately before `seal`. It is present if and only if the document's
   branch-exception count `N` is greater than zero. It is absent, rather than
   present as an empty object, if and only if `N` is zero.

   The sidecar has exactly these members, in this displayed order:

   ```text
   schema_version
   authority_kind
   document_completeness_claim
   closed_gap_disposition
   closed_gap_reason
   branch_exception_count
   dependent_atom_count
   branch_exception_records
   dependent_atom_consequence_records
   page_census_rows
   later_assembly_consequence
   status
   ```

   Their fixed scalar values are:

   ```text
   schema_version = rq_stage2_raster_only_incompleteness_census_nonauthority.v1
   authority_kind = sealed_nonauthority_sidecar
   closed_gap_disposition = CLOSED GAP
   closed_gap_reason = raster_visible_text_absent
   later_assembly_consequence = fail_or_withhold_exhaustive_flow_outputs_without_global_gap_rows_nodes_or_ids
   status = complete
   ```

   `branch_exception_count` is `N`, a positive integer excluding booleans.
   `dependent_atom_count` is `M`, a nonnegative integer excluding booleans.
   `branch_exception_records` is the complete canonical ordered array of the
   exact rule-1 records. `dependent_atom_consequence_records` is the complete
   canonical ordered array of the exact rule-2 records. No other array name or
   record shape is lawful.

   `page_census_rows` exact-covers every sealed questionnaire page, including
   pages with two zero counts and two empty key arrays, in page-number order.
   Each page row has exactly these members, in this displayed order:

   ```text
   questionnaire_page_id
   source_document_id
   interview_wave
   page_number
   page_text_utf8_sha256
   branch_exception_count
   branch_exception_keys
   dependent_atom_count
   dependent_atom_keys
   ```

   The first five fields deep-equal the sealed page row. The branch count is
   the length of `branch_exception_keys`; that array is the complete same-page
   projection of `[questionnaire_page_id, exception_index_on_page]` keys in
   the global branch-exception order. The dependent count is the length of
   `dependent_atom_keys`; that array is the complete same-page projection of
   `[questionnaire_page_id, utf8_byte_start, utf8_byte_end, occurrence_kind]`
   keys in the global dependent-record order. Concatenating page key arrays in
   page order exactly reproduces the corresponding global key domain. Page
   branch counts sum to `N`, and page dependent counts sum to `M`. `N` counts
   specific printed branch-label instances, not pages, descriptions, or
   distinct byte strings.

   An affected seal appends exactly three entries to
   `row_domain_seal_rows`, immediately after the existing
   `correction_note_rows` entry, in this order:

   ```text
   row_domain = raster_only_branch_exception_records
   row_key_fields = [questionnaire_page_id, exception_index_on_page]

   row_domain = raster_only_dependent_atom_consequence_records
   row_key_fields = [questionnaire_page_id, utf8_byte_start, utf8_byte_end, occurrence_kind]

   row_domain = raster_only_page_census_rows
   row_key_fields = [questionnaire_page_id]
   ```

   Each entry retains the existing exact five-member row-domain-seal schema:

   ```text
   row_domain
   row_count
   row_key_fields
   row_keyset_sha256
   row_domain_sha256
   ```

   Its row count, ordered keyset digest, and ordered row-domain digest are
   computed from the corresponding nested sidecar array. The seal's
   `row_domain_seal_count` increases by exactly three, and
   `row_domain_seal_domain_sha256` is recomputed over the complete ordered
   seal-row array.

   An affected seal has exactly these members, in this displayed order:

   ```text
   row_domain_seal_rows
   row_domain_seal_count
   row_domain_seal_domain_sha256
   raster_only_incompleteness_census_sha256
   seal_status
   ```

   `raster_only_incompleteness_census_sha256` hashes the terminal-LF canonical
   JSON bytes of the complete sidecar object. `seal_status` retains its
   existing lawful value. The existing whole-artifact
   `integrity.content_sha256` is recomputed under its existing zeroed-self
   preimage law and covers the outer sidecar, all three nested domains, all
   sidecar scalar fields, the augmented seal, and the sidecar digest.

   Mutation checks MUST reject a missing, extra, duplicated, or reordered
   sidecar member, branch record, dependent record, page row, page key, or
   seal-domain row; a bad page identity or page-text hash; an inexact slice;
   incomplete emitted-ID projection; count, keyset, domain, sidecar, seal, or
   artifact-digest drift; a false claim; reason or consequence drift; reuse of
   another printed occurrence's bytes; transcription repair of a partial
   slice; root-as-row resolution; dense ordinal or occurrence-index
   recomputation; and any omitted, extra, duplicated, or reordered blocking
   exception key even after all enclosing digests are recomputed.

4. **Affected-document claim and sidecar-only CLOSED GAP.** The exact claim is
   stored only in the sidecar member `document_completeness_claim`. For
   positive `N`, its value is the following template with `{N}` replaced by
   the ordinary base-10 representation of `N` without a sign or leading
   zeroes:

   ```text
   complete-under-extraction-authority with {N} raster-only exceptions
   ```

   The claim does not relabel page rows, change page `annotation_status`, or
   convert a missing label into an occurrence or branch. It claims completeness
   only under pinned extraction authority subject to the exact sidecar; it does
   not claim complete raster-flow recovery.

   `CLOSED GAP` is solely the audit disposition inside the sealed
   `raster_only_incompleteness_census` nonauthority sidecar. No CLOSED GAP row,
   node, member, or ID is ever added to a section-19 schema or any global
   catalog. This expressly supersedes the earlier Amendment 1 instruction that
   a gap enters the global catalog. Section 19 is not amended and has no gap
   domain.

   The prohibition applies to all later assembly. No exception or census
   field name, value, record, array, description, location, statement, reason,
   consequence, status, claim, count, key, index, byte, order, hash, or digest
   may be copied into, normalized into, or used as an input or preimage for a
   global row, global node, global ID, authority ID, semantic-evidence row,
   relationship, alias, hierarchy annotation, era row, flow branch, slot,
   inventory member, or other authority-bearing output. The sidecar's sole
   lawful later-assembly effect is to force the applicable fail-or-withhold
   gate. Even that Boolean gate is never serialized into an authority preimage.

5. **Fail-closed global consumption.** Exact-schema Q5 MUST fail or remain
   withheld when any input document carries the sidecar. Every other output
   whose contract requires exhaustive flow coverage MUST likewise fail or be
   withheld. A consumer MUST NOT create a gap row, default a missing branch,
   narrow a denominator, treat the gap as compatible evidence, or infer or
   synthesize a label, span, hash, occurrence, branch ID, parent, path,
   compatibility, root status, unconditional status, or semantics from the
   raster, diagnostic metadata, OCR, nearby extraction text, another printed
   occurrence, or any sidecar value.

   A rule-2 occurrence emitted on independently resolving extraction-authority
   paths applies only on its serialized resolving paths. A consumer MUST NOT
   extend it across a blocking exception. A withheld atom remains absent from
   authority outputs, and neither it nor its sidecar record may create a
   global node, row, alias, relationship, or ID. The reason remains sealed in
   the nonauthority sidecar and is never promoted into a section-19 output.

6. **Invariance.** This correction is purely additive. The 74 clean seals
   remain valid unchanged. A document with `N == 0` retains its existing outer
   schema, four-member seal, status, bytes, IDs, hashes, digests, and claim; it
   has no empty sidecar, added seal-domain row, sidecar digest, reseal, or claim
   change. Existing page, occurrence, branch, candidate-adjudication,
   output-adjudication, correction-note, and manual-add schemas remain
   unchanged except for the narrow affected-artifact index and ordinal
   refinements stated in rule 2. Every other original rule and abort remains
   in force. Section 19 remains byte-for-byte unamended.
