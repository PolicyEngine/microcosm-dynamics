# R_Q stage-1 build progress

## State

- Branch: `claude/ce-global-q5-extraction`
- Starting commit: `2bb14b514983254b5af78d74ce728ac598a319b7`
- Scope: the section 19 source replay and explicitly nonauthority candidate
  preparation consumed by per-document stage-2 annotation lanes.
- Status: source-replay parent and deterministic candidate tooling complete;
  candidate generation is sealed through batch 6 of 9 (documents 1--60). No candidate is an annotation,
  no candidate may select the source
  denominator, and no Q5, relationship catalog, or other authority artifact is
  emitted by this lane.
- External final-report target:
  `/Users/maxghenis/m6-sol-lanes/sol-ce-rq-stage1.out`.

## Done

- Read the complete R_Q scoping report and the controlling section 19 source,
  occurrence, flow, locator, catalog, and build-order laws.
- Confirmed the worktree is clean at the requested starting commit and that the
  existing global-Q5 evidence already contains replay mechanics for both roots,
  both complete disposition complements, all 257 source files, 81 questionnaire
  documents, pinned Poppler extraction, and 10,190 pages.
- Confirmed the stage-1 build must expose those mechanics as an independently
  validated parent before any candidate artifact is read.
- Built the dedicated nonauthority source-replay parent. It reconstructs both
  pinned Git roots and all four capture inputs, exact-covers the 465 link and
  456 accepted-document disposition relations, reproduces all 257 U files and
  the exact 81-document questionnaire slice, and re-extracts all 10,190 pages.
- Corrected the replayed Poppler authority member from the prior evidence's
  legacy `path` spelling to section 19's exact `implementation_path`; the
  resulting 13-key value is 566 canonical bytes with SHA-256
  `8ce4d7e16753aa0a6c2220006c9aea60330acd62de809db5894ad03eb9123da3`.
- Added mirrored validation for row schemas, ID preimages, order, counts,
  keysets, domains, role/page/era covers, candidate nonselection, and coherent
  mutation rejection. Twelve always-runnable tests and two capture-backed
  reproduction tests pass.
- Built deterministic candidate detection for all ten section 19 occurrence
  kinds with exact UTF-8 byte spans and hashes, complete candidate page cover,
  bounded acyclic flow-path alternatives, local anchor-classification and
  possible-parent rows, per-document payload manifests, fixed ten-document
  batch manifests, and a global per-era census index builder.
- Every candidate identifier uses an `rq-candidate-*` namespace. Candidate
  artifacts prohibit auto-promotion, assign no canonical node IDs, and require
  explicit stage-2 adjudication for every eventual annotation row. Eight
  synthetic unit tests cover kind order, Unicode spans, deterministic IDs,
  empty pages, flow alternatives, anchor parents, manifests, and nonpromotion.
- Sealed candidate batch 1: documents 1--10, 559 pages, 10,679 occurrence
  candidates, and batch-manifest raw SHA-256
  `b3a4152a838fcd4c9aba4f6e71c608e430367fd1d6237c7fe5f25b5a68d6fd40`.
- Sealed candidate batch 2: documents 11--20, 554 pages, 10,056 occurrence
  candidates, and batch-manifest raw SHA-256
  `f69ccd13caf5335bed44499b9aa930ed645f1c53e18a9297215411c8acf5c63e`.
- Sealed candidate batch 3: documents 21--30, 850 pages, 14,643 occurrence
  candidates, and batch-manifest raw SHA-256
  `a6dc88d41b4754f839ffe1b6ce22acfd90a0088c732cd4eda76fe15d26df20c6`.
- Sealed candidate batch 4: documents 31--40, 1,138 pages, 24,999 occurrence
  candidates, and batch-manifest raw SHA-256
  `b303e7cab9d10298efefee0f512f9a4ecc2efe6afbb2c869df2a5104ddde6c6c`.
- Sealed candidate batch 5: documents 41--50, 1,367 pages, 30,167 occurrence
  candidates, and batch-manifest raw SHA-256
  `a0b4c14fefb3007450acc4a43b15a9ed7c19d5581834f7fcdb578a67cc897836`.
- Sealed candidate batch 6: documents 51--60, 1,250 pages, 30,401 occurrence
  candidates, and batch-manifest raw SHA-256
  `2f3cf34fc9e38fcc3ec51ee5ac9cb0714eecd15b453d67ad8697dfac161b5479`.

## Next

- Generate the 81 per-document artifacts in ten-document commit batches, publish
  the stage-2 protocol, and run reproduction plus tier-sync tests.
