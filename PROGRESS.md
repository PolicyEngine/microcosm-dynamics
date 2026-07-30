# Unit 1 Round 3 Progress

## State

- Branch: `claude/ce-impl-extraction`
- Baseline: `2ff590d`
- Current phase: add exhaustive, source-hash-reproduced V-B7 rejection rows.
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
- Replaced the passing fixture's invented one-key rounding object with the
  exact seven-key null-tagged shape.
- Enforced exact B2/B11 source-cell IDs and ordering, literal vintage-2
  identity, ASCII year equality, role/status/source-class derivation, all 15
  family loss assignments, hard-zero and positive-weight domains, exact
  selection matrices and tolerances, and available/unavailable selector laws.
- Enforced both rounding tags and prohibited verified rounding for every
  B2/B11-derived target whose committed operand rules are unverified.
- Kept opaque observation/physical/ancestry resolution at the full-registry
  boundary; row-local validation does not invent an ID grammar, and full
  registration still aborts before claiming foreign-key or weight authority.
- Exact-schema/evidence focused tests pass: `111 passed`.

## Next

1. Add hash-reproduced rejection coverage for every omitted V-B7 candidate.
2. Run Black at line length 79, required suites and tail checks, then record
   the final disposition and exact verification results.
