# Context-report referee remediation

## State

- Branch: `claude/context-report-impl`
- Starting commit: `a139b3fea23661d97cd93527bc8a66737edea55b`
- Referee verdict: `FIX-FIRST`
- Active work: final review, tier/full-suite verification, push, and
  per-finding output report.
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
- Finding 2 implemented:
  - the initial attempt now reserves a unique retry-authority inode, commits a
    coordinator-only random nonce in its durable claim, and retains the nonce
    only in an opaque live token;
  - only an eligible external preparation/compute failure with the internal
    no-yield predicate can reveal that nonce, after the coordinator publishes,
    reopens, canonical-checks, schema-validates, and hashes its own incident;
  - retry adjudication authenticates the unchanged configuration, original
    attempt bytes and inode, reserved authority inode, nonce commitment,
    persisted literal no-yield predicate, and exact incident path/index/bytes;
  - the retry branch reuses the pre-existing attempt, returns an
    unconstructible live authorization, and consumes it in an authority-bound
    O_EXCL retry claim before any input operation;
  - hard crashes, absent/partial/noncanonical or inode-replaced authority,
    mutations of every authority field, attempt/incident mutation, raw
    integers/paths, and forged token objects all fail closed without creating
    a retry claim.
- Finding 3 implemented:
  - the stdlib-only launcher descriptor-gates a single committed canonical
    file under `docs/registrations`, rejects production paths and their
    symlink/hardlink/reverse aliases before reading, and exact-checks the
    production configuration including frozen-registry digests;
  - checkout, interpreter, and pycache-sentinel guard failures with a valid
    registration now append and fsync the next canonical nine-key
    preparation incident before exit, without importing or calling the
    coordinator;
  - invalid or protected registration paths retain the reader-free procedural
    refusal because no lawful registered echo exists;
  - regression probes cover every reported pre-import refusal, contiguous
    incident 1→2 publication without overwrite, and protected aliases.
- Finding 4a implemented:
  - the public incident validator no longer accepts a caller-supplied mapping
    or artifact-existence bypass; it owns the named on-disk bytes and always
    enforces the partial-primary iff rule;
  - incident files are opened through a pinned no-follow descriptor chain and
    must be canonical, bounded, regular, singly linked, and inode/size-stable
    through the read;
  - coordinator history, retry sealing, the launcher probe, and rehearsal now
    use the on-disk validator;
  - regressions reject pretty/trailing bytes, missing files, symlinks, FIFOs,
    hardlinks, oversized files, inode exchange, positional mappings, and the
    removed bypass.
- Finding 4b implemented:
  - the initial attempt claim now embeds a canonical full prelaunch record
    containing the ordered six passed checks, full registered configuration,
    ratification and implementation identities, exact input identities,
    output absence and incident contiguity, registered/actual invocation, and
    the complete acknowledged execution law;
  - the sole retry claim embeds the second invocation's corresponding six
    checks while retry authorization verifies the original attempt's record;
  - both records are durably written before the observer boundary and any
    input load, and capability/retry checks bind their exact bytes and inodes;
  - the production observer validates rather than discards the record, and
    delete/reorder/evidence/echo/argv/index mutations fail before input load.
- Finding 5 implemented:
  - the raw-row independent oracle now hardcodes model and official formulas
    for all seven available comparisons, including adjusted payroll, gross
    contributions, net payroll-tax contributions, and awards per worker;
  - an exact ordered coverage assertion pins the independent seven-ID tuple to
    the available projection of the frozen registry;
  - every comparison independently checks all 20 draws and eight annual rows,
    including both sample standard deviations and all published statistics.
- Focused launcher/report/publication/coordinator/rehearsal suite: 184 passed.
- Black, Ruff, and `git diff --check` pass through finding 5.
- Before the final security probe was added, full collection assigned exactly
  one tier to 3,867 tests: 912 unit, 1,472 artifact, 804 integration-PSID, 520
  legacy reproduction, and 159 PolicyEngine-oracle tests. The tier manifest
  will be refreshed after the probe count is collected.
- An independent security review reproduced one residual direct-core bypass:
  a caller could select production mode, inject no-op checks and a fake
  capability mint, then use the real publisher/sealer to manufacture an
  authenticated retry authority.
- The production core now refuses entry before parsing or filesystem effects
  unless a constructor-blocked invocation authority was issued by the public
  runner closure and is live on the exact runner→core stack, with the original
  root, descriptor-gated registration bytes, argv, and operation bundle.
- The runner revokes invocation authority in a `finally` block. Regression
  probes show that direct-core and extracted-issuer calls cannot reach a
  mocked production input, capability mint, claim, incident, or retry
  authority. The complete coordinator suite passes with 61 tests.
- Follow-up audit found that the generic durable-record reader could be
  pointed at a production input even though schema validation later rejected
  its contents. Durable-record reads now require a fixed claim or incident
  basename directly under `runs`, preflight the singly-linked regular inode,
  and reject direct, hardlink, symlink, and reverse-symlink aliases of either
  production input before `os.read`.

## Next

- Closure-bind the production core/verifier and coordinator-origin retry
  adjudication against the independent review's global-substitution probes.
- Run Black, Ruff, tier tests, and the full test suites.
- Record per-finding dispositions, final verification, and push status.
