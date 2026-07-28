# Progress

## State

The code-tree identity guard is implemented; real-git regressions are next.

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

## Next

- Add real-git regression fixtures and run the required checks.
