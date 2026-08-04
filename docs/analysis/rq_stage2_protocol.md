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
