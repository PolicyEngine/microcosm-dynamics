# R_Q stage-2 document 12 local-edge raster addendum

Status: controlling document-specific build law for
`document_source_position == 12` and no other document.

This addendum incorporates Amendment 1 and corrections 1–3 from
`docs/analysis/rq_stage2_protocol.md` at commit
`64aec672346534fde8e6b94e06bbdc0111c3379f`. It records the assignment's
later artifact-scale law, which forbids serialized parent-path products and
requires direct local parent occurrence relations. It changes no source-text
authority, candidate-nonselection law, section-19 occurrence kind, global-ID
prohibition, or nonauthority status.

## 1. Affected local-edge shape

The affected annotation schema is
`rq_stage2_document_annotation_local_edges_nonauthority.v1`. Its outer object
has exactly these 23 members in displayed schema order:

```text
schema_version
artifact_id
authority_kind
source_replay_identity
candidate_index_identity
candidate_artifact_identity
source_review_identity
document_source_position
document_source_row
whole_document_locator
questionnaire_page_rows
questionnaire_occurrence_rows
flow_branch_rows
local_anchor_classification_rows
local_repeat_alias_evidence_rows
candidate_disposition_rows
adjudication_note_rows
raster_only_incompleteness_census
output_adjudication_rows
seal
nonauthority_statement
integrity
status
```

The sidecar is immediately after `adjudication_note_rows` and before
`output_adjudication_rows` in displayed schema order. Canonical JSON retains
the repository's existing lexicographic object-member serialization.

The clean local-edge flat seal has 33 members. The affected seal appends the
ten correction-2 raster members in their exact correction-2 order and has 43
members. It does not acquire modern row-domain seal members. All surviving
ordinary rows and branches retain their local-edge IDs and direct-parent
representation.

Only direct parent occurrence IDs and their corresponding local branch edges
are serialized. A root-to-leaf parent path, path cross-product, blocked-path
enumeration, sparse pre-filter ordinal, comparison key, or composite
parent-path identifier is forbidden. Because the document-local Section E and Section F
roots restart their flows independently, the raster exception below has
`N == 1` and `M == 0`; no ordinary atom is serialized as its dependent.

## 2. Pinned exception table

The complete document-12 exception domain is:

| Page | Index | `item_identifier` | `canonical_visual_label` | `location_clause` |
|---:|---:|---|---|---|
| 4 | 0 | `D1` | `3. RETIRED` | `response box 3` |

The correction-2 grammar therefore derives only
`D1: 3. RETIRED` and
`page 4; item D1; response box 3`. These strings are diagnostic
nonauthority metadata. They cannot create or enter an occurrence, branch,
relationship, alias, anchor, authority ID, global ID, or semantic preimage.

## 3. Visual-fidelity note subtype

For this local-edge schema only, `adjudication_note_rows` is a discriminated
union with the existing candidate-note subtype and a document-specific
output-occurrence diagnostic subtype. Both subtypes retain the existing exact
four-member row shape.

The diagnostic subtype has:

```text
candidate_row_kind = stage2_occurrence
candidate_id = the exact emitted questionnaire_occurrence_id
note_code = attributable_garbled_exact_bytes_retained
note = The visible printed atom has an attributable partial or garbled pinned UTF-8 slice; the exact slice, offsets, and hash are retained without visual repair.
```

Despite the legacy field names, `stage2_occurrence` is not a candidate kind
and its `candidate_id` value is not a candidate ID. The value must resolve to
exactly one emitted occurrence. Diagnostic rows are extra rows and supersede
correction 2's legacy “existing candidate note / no extra row” carrier only
for this document-specific local-edge schema. They do not change a candidate
disposition or supply semantic evidence.

Existing candidate notes exact-cover nonaccepted candidate rows in their
existing order. Diagnostic rows follow all candidate notes and are ordered by
questionnaire-occurrence source/kind order. They are excluded from the
one-note-per-nonaccepted-candidate equation but included in
`adjudication_note_count`, `adjudication_note_domain_sha256`, and whole-artifact
integrity.

The source review pins the complete if-and-only-if diagnostic domain by exact
review occurrence ID. Its coordinate projection is:

```text
4:321:338:flow_branch_label
4:341:361:flow_branch_label
4:833:843:flow_branch_label
4:915:923:flow_branch_label
4:1739:1769:flow_branch_label
5:954:1103:context_anchor
5:954:1103:field_purpose_prompt
5:2092:2138:field_purpose_prompt
5:2429:2448:flow_branch_label
6:240:260:flow_branch_label
16:398:414:flow_branch_label
16:421:488:field_purpose_prompt
21:405:423:flow_branch_label
21:453:485:flow_branch_label
21:554:571:flow_branch_label
21:640:658:flow_branch_label
```

Exactly one diagnostic row must bind each listed occurrence, and no diagnostic
may bind any other row. Whitespace-only word joins and checkbox-spacing changes
are outside this domain. A missing, duplicate, reordered, wrongly bound, or
text-modified diagnostic is rejection.

## 4. Validation and later assembly

The validator independently reconstructs the source review, ordinary
local-edge rows, candidate/output adjudications, diagnostic exact cover,
sidecar, all ten raster seal fields, and integrity. Its affected mutation
matrix covers structure, counts, keys, order, identities, strings, diagnostics,
digests, and coherently resealed semantic mutations. Blocking-key mutations
are inapplicable because the pinned dependent domain is empty; any added
dependent record or blocking key is rejection.

The sidecar retains Amendment 1's single fail-closed later-assembly effect.
No Q5, era seal, global catalog, global alias resolution, R_Q output,
hierarchy, slot, inventory member, or legal-registry claim is emitted here.
