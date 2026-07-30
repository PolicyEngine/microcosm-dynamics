# Unit 1 Round 3 Progress

## State

- Branch: `claude/ce-impl-extraction`
- Baseline: `2ff590d`
- Current phase: inspect the ratified design, evidence boundary, exact nested
  schema laws, and retained V-B7 adjudication before changing code.
- Constraints: use committed source bytes only; keep final registration
  fail-closed; commit each coherent edit; do not push.

## Done

- Confirmed the worktree is clean at the requested baseline.
- Recorded the three exact recheck edits and the required verification queue.
- Identified `FINAL_REPORT.md` as the established final output-file convention.

## Next

1. Separate evidence-only registries from all authoritative registry APIs and
   prove evidence rows cannot be ingested as final authority.
2. Enforce the full nested calibration-target schema laws from design
   sections 6.1 and 6.2.
3. Add hash-reproduced rejection coverage for every omitted V-B7 candidate.
4. Run Black at line length 79, required suites and tail checks, then record
   the final disposition and exact verification results.
