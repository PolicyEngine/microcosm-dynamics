# Progress

## State

The ratified design and failing coordinator path are understood; implementation
is next.

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

## Next

- Replace exact-HEAD identity with code-tree identity.
- Add real-git regression fixtures and run the required checks.
