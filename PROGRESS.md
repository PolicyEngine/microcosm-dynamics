# Unit 1 Round 3 Progress

## State

- Branch: `claude/ce-impl-extraction`
- Baseline: `2ff590d`
- Current phase: implement the full nested calibration-target schema laws from
  design sections 6.1 and 6.2.
- Constraints: use committed source bytes only; keep final registration
  fail-closed; commit each coherent edit; do not push.

## Done

- Confirmed the worktree is clean at the requested baseline.
- Recorded the three exact recheck edits and the required verification queue.
- Identified `FINAL_REPORT.md` as the established final output-file convention.
- Removed the evidence loader and validator from the authoritative registry
  module and its public exports.
- Renamed all three nested identity collections and schema IDs from final
  `*_specs.v1` authority names to explicit `*_evidence.v1` names.
- Regenerated and independently pinned 1,515,381 canonical evidence bytes at
  SHA-256
  `1080acc9672abf209bb9c5ec06170ca351b26200ba1727652fd515b25b216380`.
- Proved every evidence row shape is rejected by every final-registry
  ingestion path; the evidence/registry focused suite passes: `40 passed`.

## Next

1. Enforce the full nested calibration-target schema laws from design
   sections 6.1 and 6.2.
2. Add hash-reproduced rejection coverage for every omitted V-B7 candidate.
3. Run Black at line length 79, required suites and tail checks, then record
   the final disposition and exact verification results.
