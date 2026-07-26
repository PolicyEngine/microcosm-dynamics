# Progress

## State

- The first-estimates results draft is complete on `claude/entry8-paper`.
- The required fetch was attempted twice. The sandbox first failed DNS
  resolution and then, with a current address supplied through
  `http.curloptResolve`, refused the outbound connection because network access
  is disabled.
- Read-only GitHub metadata confirms that remote `master` is
  `7b1ee30c355749884522fb11ec25aa8bea6152e8`, with parent `8b031bc3`, and
  changes only `docs/forecasts/timeline_ledger.json`. The remote file's blob
  `6c7161e8` and full patch match local commit `0f246c4` exactly. Because the
  sandbox cannot import the signed `7b1ee30c` commit object, the draft is
  provisionally rebased on the tree-equivalent `0f246c4`; exact ancestry remains
  for the coordinator to repair after a fetch.
- The source artifact is present at the required SHA-256:
  `719604ca4364e7cdef2293329ed0beb0e011e5d4d1c34f0e508c8f2fd9932977`.
- The draft adds five labeled tables, the execution and limitation record, all
  nine successors, the exact closing claim, and the matching status update.
- A full HTML-and-PDF standalone render has succeeded, and all 37 focused
  reproduction, publication, gap-block, and paper-figure tests pass.

## Done

- Confirmed the starting worktree was clean.
- Created/reset `claude/entry8-paper` from the existing local
  `origin/master`.
- Read the GitNexus exploration workflow for tracing the paper and render
  structure.
- Located the task-27 candidate-3 PASS precedent: add a sibling subsection
  after the projection-gate candidate arc and update the status paragraph.
- Programmatically extracted every requested number and its JSON path. The
  frozen birth-timing values are draw-0 values; the benefit and revenue tables
  are twenty-draw means plus sample SD.
- Confirmed the absolute table labels and closing claim, the complete
  registrations/incidents chronology, the five `certifies_nothing` statements,
  and all nine named successors.
- Chose tables only: the repository has no first-estimates chart builder, while
  its figure tooling and palette test cover committed SVGs.
- Identified `quarto render paper/paper.qmd` as the paper render command and the
  focused reproduction, publication, gap-block, and palette tests.
- Recomputed every displayed table cell from the JSON after drafting and
  machine-checked the rendered strings before committing the paper.
- Rendered `paper/paper.qmd` to HTML and PDF with task-scoped Quarto and TeX
  caches; inspected the PDF birth-timing table and confirmed the approximation
  marks render.
- Ran the four focused test modules under Python 3.13 with `PYTHONPATH=src`: 37
  passed with no warnings, skips, or failures.
- Tightened the execution paragraph to state explicitly that the sixth incident
  record was also committed append-only.
- Rebased the draft commits onto local `0f246c4`, whose tree is identical to
  remote `7b1ee30c`; no remote state was changed.

## Next

- Repeat the render and focused tests after the final prose adjustment.
- Write and commit `FINAL_REPORT.md` with the diff, every numeric JSON source,
  and all judgment calls.
- After network access is available, fetch and replace the provisional base
  with exact remote ancestry:
  `git rebase --onto 7b1ee30c 0f246c4 claude/entry8-paper`.
