# Progress

## State

Implementation and real-git regressions are complete; repository-wide
verification is next.

## Done

- Attempted `git fetch origin`; the workspace network policy could not resolve
  `github.com`.
- Reset `claude/identity-law-fix` to the locally available `origin/master`.
- Read ratified design §5: it requires a 40-hex `implementation_commit` and
  identification of the referee-gated implementation, but never equality to
  `HEAD`. This is an implementation-only correction with no design amendment.
- Traced `_validate_repository`: the clean-tree guard precedes an exact
  `HEAD == implementation_commit` comparison, and the same validator runs at
  prelaunch and immediately before publication.
- Replaced exact-`HEAD` identity with a fail-closed existence and ancestry
  check plus exact `src/` and `scripts/` tree-hash comparisons.
- Added real temporary-Git regressions for a records-only descendant, a
  committed `src/` change, and a nonancestor with matching code trees.
- Added fixture-only code roots to the rehearsal's private temporary
  repository and advanced the artifact-tier manifest by three tests.
- Targeted results: coordinator `86 passed`; rehearsal `23 passed`; tier
  policy `1 passed, 3927 deselected`.

## Next

- Run Black, Ruff, all tier collection smokes, and the full estimates suite.
