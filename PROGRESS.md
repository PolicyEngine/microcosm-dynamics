# Document 10 reseal progress

## State

The ratified Amendment 1 corrections are implemented on
`claude/ce-rq-doc10`. The regenerated legacy artifact and source review pass
their independent validator, mutation suite, and focused tests. Independent
seal review remains before the final progress-file removal and seal commit.

## Done

- Verified the worktree was clean.
- Switched from the preserved blocked-draft branch to the required seal branch.
- Confirmed the pinned seal base, blocked draft, and ratification commit are
  available locally.
- Attempted to refresh `origin`; network name resolution is unavailable, so the
  pinned local authorities will be used.
- Read all 1,193 lines of the ratified protocol at `64aec67` and reconciled its
  correction precedence, comparator, sidecar, flat-seal, diagnostic-note, and
  mutation laws.
- Imported the seven-file blocked-draft baseline without unrelated changes.
- Re-ran the baseline source-review check/census, annotation check plus mutation
  suite, and the focused validator (`17 passed`).
- Independently derived the adjudicated census: `N=10`, `M=75`; dependent atoms
  by page are 18 (page 7), 39 (page 8), 16 (page 16), and 2 (page 21).
- Retained all 13 attributable partial/garbled spans as exact pinned UTF-8,
  without visual repair, and bound each to exactly one required existing note.
- Implemented the complete ten-exception and 75-dependent-atom domains, with
  33 emitted and 42 withheld consequences and their exact blocking unions.
- Implemented frozen pre-filter flow ordinals and occurrence indices; the D8
  `SAME` witness survives at ordinal 1 and page index 27.
- Added the complete 42-page legacy sidecar, 23-member affected outer shape,
  and 40-member flat seal with all ten raster-domain additions.
- Added deep mutation coverage, including all omitted/extra/duplicate/reorder
  H7 blocker and page-key variants after recomputing every raster seal field
  and the artifact integrity digest.
- Regenerated both committed JSON artifacts. Source-review reproduction,
  annotation validation plus mutations, focused tests (`17 passed`), Ruff,
  Black, and `git diff --check` are green.
- Completed three independent read-only reviews. The case-table audit was
  clean. The protocol/code audits identified numeric-type equality and missing
  deep-mutation variants; exact JSON equality, explicit non-boolean integer
  checks, submitted-sidecar seal verification, and the complete mutation
  matrix now close both findings.

## Next

- Commit the coherent independent-review fixes and updated progress state.
- Rerun independent protocol/code review against the fixes.
- Remove this progress file in the final seal commit and write the lane report.
