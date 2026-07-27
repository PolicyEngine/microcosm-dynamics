# Context report implementation progress

## State

Implementation and fixture-only verification are complete. No production
input has been opened and no production comparison value has been computed.

## Done

- Verified the worktree was clean and on the requested branch and commit.
- Attempted to fetch `origin/master`; DNS is unavailable in the execution
  environment, and the locally recorded `origin/master` already equals the
  requested base commit.
- Verified the working design bytes equal the `origin/master` design bytes.
- Read all of `docs/design/anchor_context_extraction.md`, including the
  frozen registries, exact-complete result schema, fixture-only rehearsal
  law, and ceremony contract.
- Mapped the reusable first-estimates canonical JSON, sidecar, sealing,
  coordinator, and incident machinery.
- Added a red test for the §5.2 requirement that a sidecar publication
  failure permanently retain the partial primary report.
- Extended the shared exclusive writer with an opt-in preserve-primary mode;
  its existing rollback behavior remains the default. All 10 contract
  identity/writer tests pass.
- Added canonical, visibly fixture-only model and anchor inputs. Independent
  checks confirm exact 20-draw-by-8-year model grids, all 15 ordered
  8-year anchor series, normalized synthetic values, positive denominators,
  and pinned fixture hashes.
- Encoded the frozen 15-series, 7-metric, 14-pairing, and 9-comparison
  registries with deep-copy accessors and strict type-aware equality.
  An independent parser confirmed exact equality to the four design
  registries (15/7/14/9); ruff and diff checks pass.
- Implemented the pure comparison engine and exact-complete results
  validator. It resolves all nine operands, requires ordered 20x8 grids,
  joins flow and opening stock within draw/year, reduces ratios only after
  per-draw evaluation, and emits 56 evaluated comparison rows, two
  unavailable disclosures, 120 official levels, and 56 model levels.
- Added 21 fixture-only unit tests, including three independent formula
  recomputations and omission, duplicate, reordering, extra-ID, wrong-value,
  mismatch-array, and level-only OASI cash forgeries. All 21 pass.
- Added the canonical report configuration, artifact, input hash-gate, and
  typed append-only incident contracts. The production loader is
  registration-token gated; the fixture loader rejects either production
  path, hash, or vintage before opening any input.
- Added 43 fixture-only publication tests covering exact schemas and canonical
  bytes, hash-gate aborts, sidecar publication semantics, incident validation,
  and malformed or non-contiguous incident histories. All 43 pass.
- Implemented the fail-closed coordinator with six prelaunch checks, exact
  registered-versus-actual invocation comparison, the four ceremony phases,
  append-only incident publication, and the one-retry preparation/compute
  rule. It reuses the first-estimates lock and result/failure types.
- Added 17 fixture-only artifact-tier coordinator tests covering phase
  routing, both invariant boundaries, hash failure before engine entry,
  production-identity rejection before reads, output-absence gates,
  canonical invocation matching, frozen incident echoes, and retry law.
  All 17 pass.
- Added the one-shot isolated runner with a standard-library pre-import Git
  guard and exact `--registration` forwarding. Thirteen fixture-only unit
  tests cover clean sealed launch, unsealed/nonempty-cache refusal, dirty or
  hidden index state, ignored executable artifacts, structured refusal, the
  exact CLI surface, and terminal result serialization. All 13 pass.
- Hardened the ceremony after independent review: reports now carry the
  complete ordered prior-incident history; production artifact assembly
  requires opaque hash-gated input authority; incident validation requires
  an exact-complete production or fixture echo and contiguous suffix; and
  durable attempt/retry claims close process-death replay windows.
- Generalized the already-tested first-estimates durable-claim helpers with
  report-specific path/schema arguments instead of duplicating that
  machinery. Anchor-context claim and incident state is ignored only while
  it is ceremony-owned prepublication state.
- Expanded the fixture-only publication/coordinator coverage to 64 passing
  tests, including false production provenance, malformed self-echo,
  prior-incident carry-forward, and hard-death claim replay forgeries. The
  sealed runner tests remain 13/13 green with the canonical relative script
  path.
- Added a no-argument, sealed fixture-rehearsal entry point. It admits only
  the canonical committed fixture manifest and identities, rejects
  production path/hash/vintage aliases and source or parent symlinks before
  reads, runs success and typed-incident ceremonies in disposable private
  Git roots, and emits pass/fail metadata without fixture statistics.
- Added 14 rehearsal tests, including a real isolated subprocess through the
  engine, both validators, append-only writer, sidecar, incident path, and
  cleanup. The combined first-estimates coordinator, context publication,
  context coordinator, sealed-runner, and rehearsal selection passes
  159 tests.
- Ran Black 25.11.0 at line length 79 and Ruff on the complete changed Python
  surface; both pass.
- Recollected all 3,798 tests by tier and updated the enforced manifest:
  920 unit, 1,395 artifact, 804 integration-PSID, 520 legacy reproduction,
  and 159 PolicyEngine-oracle tests.
- The first complete suite run exposed one intended historical-identity
  guard: adding context-only modules and the opt-in writer mode changed the
  broad source tree without changing the first-estimates computation. The
  historical reducer now excludes an exact pinned list of these post-review
  sources, while its original estimator surface and coordinator remain
  byte-for-byte unchanged. Anchor durable claims use the shared lock,
  canonical JSON, safe reason types, bounded write primitive, and sealed
  runs-directory guard without modifying the frozen first-estimates
  coordinator.
- Closed the final independent-review findings: the opaque production-input
  authority now freezes canonical snapshots and rejects either decoded
  document if it mutates after the byte hash gate; the coordinator freezes
  the ordered six-check prelaunch record and a test proves it exists before
  input loading.
- Kept the shared writer on the historical reducer's fail-closed surface by
  pinning its exact post-review Git blob in both HEAD and the worktree; only
  the separately named context modules are excluded without a shared-source
  byte pin.
- Received a clean final independent ceremony audit after the review fixes;
  the audit found no remaining actionable issue in the §§4–5 scope.
- Re-ran Black 25.11.0 at line length 79 and Ruff over all 17 changed Python
  files; both pass.
- Ran the complete estimates/publication selection: all 369 tests pass in
  19.98 seconds.
- Ran the sealed, no-argument fixture rehearsal as an isolated interpreter.
  All five public checks pass: fixed fixture identity, success ceremony and
  validators, canonical sidecar publication, typed incident publication,
  and private-root cleanup.
- Recollected the final tier manifest: all five selections match their
  committed counts and sum to 3,798 tests.

## Next

- Commit this final verification record and push the completed branch.
