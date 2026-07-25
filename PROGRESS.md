# PR #286 Fix Round 8 Progress

## State

- Branch: `sol/entry8-impl`
- Starting tip: `8172e7c`
- Review/adjudication: read and reconciled
- Implementation: Git guards hardened; regressions pending
- Verification: pending
- Push: pending
- Final report: this file

## Done

- Confirmed the requested worktree, branch, clean starting tree, and starting tip.
- Loaded the PR review-comment workflow.
- Read the latest two PR #286 comments: the round-8 FIX-FIRST review and its
  accepted adjudication.
- Confirmed the two required work areas:
  - bind both guards to the sealed repository while scrubbing all inherited
    `GIT_*` routing variables and refusing lowercase `git ls-files -v` flags;
  - isolate the CLI success test in a temporary repository and audit every
    other test for unmocked access to the live guard.
- Hardened the launcher-side and coordinator-side Git helpers to:
  - remove every inherited `GIT_*` variable from the child environment;
  - invoke `git -C <sealed-root> --git-dir=<sealed-root>/.git`;
  - verify `rev-parse --show-toplevel` resolves to the sealed root.
- Made both guards reject every lowercase `git ls-files -v` tag and the
  uppercase `S` tag that Git uses for skip-worktree alone.
- Confirmed the explicit Git route accepts this linked worktree's `.git`
  gitfile and both hardened helpers accept its ordinary index flags.

## Next

1. Add the Git-routing and hidden-index regressions.
2. Fix the CLI success test and finish the live-guard test audit.
3. Run the full local fast suites and repository quality checks.
4. Update this final report, commit every coherent step, and push if DNS allows.
