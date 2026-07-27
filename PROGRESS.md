# Context-report referee remediation

## State

- Branch: `claude/context-report-impl`
- Starting commit: `a139b3fea23661d97cd93527bc8a66737edea55b`
- Referee verdict: `FIX-FIRST`
- Active work: finding 2, replacing structural retry classification with
  authenticated, attempt-bound provenance and a persisted no-yield proof.
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
- Finding 1 implemented:
  - the production capability mint exists only in the sealed public runner's
    closure, rejects extracted/out-of-stack calls, and runs after the six
    checks and canonical attempt claim;
  - the injectable rehearsal runner receives only a registration token and a
    fixed-hash, loader-issued fixture bundle, never production authority;
  - every model extraction, build, result validation, artifact validation,
    and production write authenticates either that fixed fixture bundle or
    the live production capability plus its exact hash-gated input bundle;
  - capability checks bind the original claim path, canonical bytes, inode,
    registration, and lifetime, and revocation is verified after return;
  - input descriptors reject non-fixed identities, symlink components,
    hardlinks, reverse aliases, cross-role capabilities, and production
    aliases before reads;
  - the public registration path is lexically classified and then opened,
    inode-checked, bounded, and read through one pinned no-follow descriptor
    chain while holding the ceremony lock.
- Added the referee's mocked outside-ceremony probes plus forged fixture
  markers, fixture/production authority crossover, claim replacement,
  revocation, production-input hardlink, and registration hardlink/symlink
  regressions.
- Fixture publication is issuance-bound to the exact temporary rehearsal root;
  alternate checkouts and mutation of the bundle's root are rejected.
- Focused report/publication/coordinator/rehearsal suite: 122 passed.
- Black, Ruff, and `git diff --check` pass for the finding-1 change set.

## Next

- Implement findings 2–5 in separate coherent commits with dispositions.
- Run Black, Ruff, tier tests, and the full test suites.
- Record per-finding dispositions, final verification, and push status.
