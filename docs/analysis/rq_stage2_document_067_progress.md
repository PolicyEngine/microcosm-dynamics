# R_Q stage-2 document 067 progress

## State

- Sealed source review and annotation are complete on
  `claude/ce-rq-doc67`, based on the sealed stage-1 tip `8088484`.
- Scope is exactly `document_source_position: 67` and one nonauthority
  per-document annotation shard.
- Artifact
  `rq-stage2-document-annotation:fde1f12a362c27f22748a1621f0b27e3dbf2a812014e7e23d897da7220a63463`
  has status `sealed_complete_nonauthority_document_annotation`; it assigns
  no final global IDs.

## Done

- Verified the worktree is clean, isolated, and at the assigned stage-1 tip.
- Confirmed that no final Q5, global catalog, alias, relationship, slot,
  inventory, crosswalk, reader, or legal-registry identifiers may be emitted.
- Confirmed every candidate and every emitted row needs explicit, bidirectional
  adjudication after review of the authenticated source page bytes.
- Reauthenticated document 067 as wave-2005 `q2005.pdf`, source document
  `psid-source-document:715a2b2c104319c44abdded4c76b1e7abda7014af657c6c2a2ba861081d3888b`:
  1,013,400 bytes, SHA-256
  `d804ddd0b61f09d66c939de029b06f54b58295e539c214b6eacdef7d904e799c`.
- Re-extracted all 179 pages with pinned Poppler 26.04.0 and reproduced every
  replayed page size and SHA-256 with zero mismatches.
- Reproduced the position-67 candidate artifact byte-for-byte and validated its
  exact index/batch joins: 3,796 occurrence, 2,461 flow-path, and 1,062
  anchor-classification candidates over 179 candidate page rows.
- Passed all 12 focused source-replay tests and the position-67-only candidate
  validator/reproduction path without reading downstream authority inputs.
- Reviewed all 179 authenticated q2005 pages, including 132 pages with no
  retained R_Q occurrence. The 47 occurrence-nonempty pages cover BC/DE
  employment, G labor-income/job linkage, P current/former-plan work anchors, KL
  respondent-career ancestry, and R Head/Wife T-2 labor-income loop. Worklike
  housing, wealth, transfers, health, OFUM, parental-history, education,
  volunteer, and nonlabor-income prose was explicitly excluded.
- Committed source-review input has 1,197 exact source specs: 190 flow, 86
  role, 211 job, 100 remuneration, 4 role-total, 12 farm, 77 business, 217
  context, 276 purpose, and 24 repeat/cross-reference atoms. Multipath branch
  expansion produces 1,212 occurrence rows and 205 flow branches.
- Built exact local cover with 707 anchor-classification rows and 24 local
  repeat/alias-evidence rows. No final catalog, component, alias,
  relationship, hierarchy, Q5, era-seal, inventory, or legal-registry row was
  emitted.
- Adjudicated all 7,499 stage-1 candidate rows: 1 locator, 179 pages, 3,796
  occurrences, 2,461 flow paths, and 1,062 anchor classifications. Overall
  dispositions are 1,195 accepted, 1,140 modified, 9 split, and 5,155
  rejected; 132 emitted occurrence rows are source-reviewed manual additions.
- Passed deterministic annotation byte comparison and all structural mutation
  gates, including omission/reordering, span/hash/ID/ordinal drift, duplicate
  atoms, unresolved/later/cyclic/omitted/duplicate branches, selected-path
  subsets, inferred aliases, and incomplete provenance cover.
- Passed the stage-1 source-replay, batch-07, and index `--check` builders; the
  12 focused source-replay tests; `ruff check`; Black check; and repository
  whitespace checks. No test or tier-count file was added or changed.

## Next

- Hand the committed document-local shard to the later global
  catalog/alias/R_Q stage; that later stage alone may assign final global
  component and relationship IDs.
