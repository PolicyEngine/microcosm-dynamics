# Context-report referee remediation

## State

- Branch: `claude/context-report-impl`
- Starting commit: `a139b3fea23661d97cd93527bc8a66737edea55b`
- Referee verdict: `FIX-FIRST`
- Active work: finding 1, replacing caller-constructible production authority
  with a coordinator-issued ceremony capability and sealing the registration
  path before its first read.
- Remote sync: `git fetch`/`git pull --ff-only` was attempted first, but the
  sandbox could not resolve `github.com`; the checked-out commit matches the
  existing local `origin/claude/context-report-impl` ref.

## Done

- Verified the requested clean worktree, branch, and starting commit.
- Read `/Users/maxghenis/m6-sol-lanes/sol-context-referee.out` through EOF.
- Confirmed that the verdict contains five ranked findings.
- Read the ratified executable ceremony contract in design section 5.
- Independently mapped every finding to the current code, the complete design,
  and the first-estimates coordinator:
  1. Gate production reads and every production computation behind a
     coordinator-only capability minted after the six checks, durable attempt
     claim, and exact invocation seal; reject production inputs masquerading
     as registration files before any read.
  2. Require a pre-existing attempt claim plus coordinator-authenticated,
     digest-bound incident provenance that persists and proves the no-yield
     predicate before authorizing the sole retry.
  3. Publish typed incidents for the launcher’s checkout, interpreter, and
     pycache-sentinel preparation refusals.
  4. Make the public incident validator read and canonical-check the file at
     its path, remove the artifact-existence bypass, and persist concrete
     evidence for all six prelaunch checks.
  5. Extend the independent formula oracle from three to all seven available
     comparisons.
- Confirmed that the referee reported the frozen registries, arithmetic,
  selectors, and exact-complete result validator clean; those surfaces will
  not be churned beyond the required authority boundary.

## Next

- Implement finding 1 and its outside-ceremony/path-confusion probes.
- Implement findings 2–5 in separate coherent commits with dispositions.
- Run Black, Ruff, tier tests, and the full test suites.
- Record per-finding dispositions, final verification, and push status.
