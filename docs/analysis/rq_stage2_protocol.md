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
