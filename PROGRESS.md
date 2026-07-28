# Context-report referee remediation

## State

- Branch: `claude/context-report-impl`
- Starting commit: `a139b3fea23661d97cd93527bc8a66737edea55b`
- Referee verdict: `FIX-FIRST`
- Active work: closing the final adversarial review findings across the
  launcher, publication authority, and coordinator, followed by a clean
  re-review, tier/full-suite verification, push, and per-finding output
  report.
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
- The runner revokes invocation authority in a `finally` block. Initial
  regression probes showed that direct-core and extracted-issuer calls could
  not reach a mocked production input, capability mint, claim, incident, or
  retry authority.
- Follow-up audit found that the generic durable-record reader could be
  pointed at a production input even though schema validation later rejected
  its contents. Durable-record reads now require a fixed claim or incident
  basename directly under `runs`, preflight the singly-linked regular inode,
  and reject direct, hardlink, symlink, and reverse-symlink aliases of either
  production input before `os.read`.
- The incident descriptor gate now compares mode, link count, size, mtime,
  and ctime as well as device/inode against both the open descriptor and the
  canonical name after reading. An equal-length, same-inode rewrite during
  `os.read` is rejected instead of validating stale bytes.
- Independent substitution probes found that the first entry fix still
  resolved the core and invocation verifier through mutable module globals.
  The protocol now constructs the core as a verifier-capturing closure; the
  public runner, capability mint, invocation verifier, and retry stack all
  bind that exact core/code rather than looking up a replaceable global.
- Retry adjudication now requires exact retained coordinator-origin state
  created only after the live initial authority publishes, reopens, and seals
  its incident. A caller-fabricated but internally consistent attempt,
  incident, nonce, and authority chain cannot mint a retry token or claim.
- Because retained origin state is intentionally process-local, the supported
  public coordinator now owns both attempts: after publishing and retaining
  an eligible no-yield incident, it performs the sole retry under the same
  lock, unchanged registration bytes/argv/operations, and a fresh sealed
  invocation authority. It never exits between adjudication and retry.
- Frozen nested prelaunch evidence now uses type-exact JSON comparison, so
  `true` cannot substitute for integer incident index or `registered_runs`.
- Retry-claim creation now captures the exact live authorization verifier in
  a deleted protocol closure; callers cannot inject a forged verifier as a
  hidden keyword argument.
- A final finding-1 callable inventory exposed five residual substitution or
  alias paths. All five now fail before production input bytes or computation:
  - raw descriptor helpers use a one-call path-bound authority, exact loader
    stack, stable metadata, a byte bound, and immediate revocation; even an
    extracted helper plus a caller-added registry entry cannot reach
    `os.open`;
  - both production input protocols bind the exact ceremony-capability
    verifier once from the coordinator's initialization frame, and their raw
    loader dependencies are closure-captured;
  - every report extraction/build/validation entry closure-captures the
    original document authorizer and downstream engine callable, so rebinding
    module globals cannot produce the 9/15/7 result sections;
  - the public runner captures the canonical repository root value, lock,
    descriptor-gated registration reader, core, and exact production
    operation bundle before the protocol factory is deleted;
  - rehearsal manifest and fixture sources are opened only through bounded,
    no-follow descriptor chains that reject direct production paths,
    hardlinks, symlinks, reverse aliases, unstable metadata, and oversized
    files before `os.read`.
- Direct attempts to pre-bind fake publication or report verifiers are
  rejected unless the immediate caller is the exact coordinator protocol
  initialization frame.
- The combined launcher/coordinator/publication/rehearsal/report regression
  suite passes with 214 tests after the final closure and alias probes.
- Full collection assigns exactly one tier to 3,897 tests at current HEAD:
  924 unit, 1,490 artifact, 804 integration-PSID, 520 legacy reproduction,
  and 159 PolicyEngine-oracle tests.
- Unit tier: 919 passed, 5 skipped, with all 2,973 other-tier tests
  deselected; the full-collection tier policy accepted the refreshed
  manifest.
- Artifact tier: 1,450 passed, 40 skipped, with all 2,407 other-tier tests
  deselected.
- The next adversarial pass found four contract-level residuals: a fake
  coordinator module could pre-bind publication verifiers; the public runner
  could be cloned with replacement closure cells; fixture and public
  execution-law identities were mutable; and durable authority reads did not
  yet reject every static hardlink before opening or detect every
  same-inode rewrite.
- The launcher half of that hardening is complete:
  - canonical registration metadata, including link count and protected-inode
    checks, is validated before the leaf descriptor is opened;
  - coordinator import and entry failures publish exactly one append-only
    preparation incident, while a coordinator-written incident is detected
    and never duplicated;
  - a Git-unavailable checkout can recover only the exact configuration echo
    through the same descriptor-gated registration path, while a functioning
    Git object database still enforces committed-byte equality; and
  - malformed incident-prefixed names fail closed instead of being ignored.
- Launcher regressions cover clean committed import failure, an entry point
  that writes then raises, unavailable Git, live-Git mismatch, malformed
  names, and direct/reverse hardlink and symlink aliases. The focused launcher
  suite passes with 29 tests; per-file Black, Ruff, and `git diff --check`
  pass.
- Independent launcher review then found that `SystemExit` could bypass the
  entry-failure handler and that persisting an unexpected exception string
  could copy estimate-bearing text into `reason_detail`. The handler now
  catches every `BaseException` and uses one fixed non-estimate-bearing
  detail for all unexpected coordinator import/entry failures. RuntimeError
  and SystemExit probes with statistic-like messages confirm that neither the
  incident nor stdout/stderr contains them; the launcher suite now passes 30
  tests.
- The final finding-1 authority hardening is integrated:
  - publication exposes only a transient, self-deleting coordinator verifier
    handshake and authenticates the exact compiled canonical coordinator
    module code, module object, import state, and source origin; fake modules,
    forged canonical-filename frames, and post-import clones cannot pre-bind
    or replace it;
  - the report verifier handoff is likewise one-use and internal to
    publication, eliminating the three persistent binder surfaces;
  - fixture path/hash/vintage identities are literal closure state used by
    validation, loading, and computation even if public names are rebound;
  - fixture rehearsal rejects hardlinks and protected production-input inodes
    before a leaf open or read, while every opened input rechecks both its
    descriptor and canonical leaf name after reading; and
  - public runner clones, substituted closure dependencies, direct core/mint
    calls, and forged capabilities fail before the ceremony lock, production
    input I/O, or report computation.
- The final finding-2 coordinator hardening is integrated:
  - constructible retained provenance and caller-populatable retry registries
    are gone; the first attempt returns an explicit one-shot receipt that is
    usable only by the same public coordinator's uninterrupted second loop
    iteration;
  - the receipt authenticates the coordinator's exact published incident,
    durable attempt and authority records, unchanged configuration,
    `production_only` mode, and persisted `estimate_bearing_information_yielded:
    false` predicate before the retry claim is created, then is consumed;
  - all claim readers pin and recheck mode, link count, size, timestamps,
    device/inode, and canonical name; registration hardlinks and protected
    aliases are rejected before leaf open; and
  - the execution law is retained as private immutable canonical bytes, with
    only a read-only public view.
- A real exported-public-runner fail-once regression confirms that the public
  coordinator owns both attempts, creates exactly one report-first retry
  claim, and never exposes the receipt. Coordinator, publication, and report
  focused suites pass together with 183 tests.
- Independent finding-4 review found a remaining directory-exchange race in
  incident validation: the leaf descriptor remained stable while the
  canonical `runs` name could be replaced. The validator now pins and
  post-read rechecks the repository root, `runs` directory, and leaf metadata
  chain. The concrete old-directory/new-directory probe is rejected while
  confirming the canonical path contains the replacement; the publication
  suite passes 74 tests.
- Independent finding-5 review approved the complete oracle: all seven
  available formulas are hardcoded independently across 20 draws and eight
  years, covering 1,120 model cells, 56 official cells, 1,120 comparison
  cells, and all 280 published annual numeric fields.

## Next

- Obtain an independent clean re-review of every referee disposition.
- Run Black, Ruff, each tier, and the full test suite.
- Record per-finding dispositions, final verification, and push status.
