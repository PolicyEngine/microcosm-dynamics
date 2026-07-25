# PR #286 fix round 2

## State

Implementation and local verification are complete on `sol/entry8-impl`. No
projection was run and no launcher or process-persistence mechanism was
installed; the adjudicated durable attempt claim is the only new persistent
state. Push is blocked only because this sandbox cannot resolve `github.com`.

## Done

- Read the latest two PR #286 comments: the round-2 conformance review and the
  coordinator's scoped adjudication.
- Merged `origin/master` at `ee1221d`, preserving master's amended design text.
- Confirmed that LaunchAgent, `nohup`, and `caffeinate` mechanics are expressly
  run-time procedure and must not be installed by library or CLI code.
- Implemented the exact one-key deferred context-ratio disclosure.
- Copied the amended 33-line section 10 table byte-for-byte into the fixture
  and runtime gap block, pinned at SHA-256
  `b2330953bf4b517b1bc8f113c596fda0a5d6c60ca240a5cfd232a58346227977`.
- Bound the registered configuration to ratification `6586b92` and amendment
  `ee1221d`; 28 focused amendment tests, Black, Ruff, and diff checks pass.
- Moved raw configuration-path reading, byte parsing, and structural validation
  under the coordinator's incident boundary; invalid, malformed, changed, and
  noncanonical bytes now publish preparation incidents.
- Removed the CLI repository override and sealed production to the repository
  containing the imported estimates package. The canonical `runs` directory,
  lock, configuration path, all nine estimator modules, and registered input
  chain are enforced against that root and committed `HEAD`.
- Added an exclusive, fsynced `runs/first_estimates_attempt.claim` before any
  operation. It is never removed automatically and refuses same or different
  registrations pending explicit fresh-registration adjudication.
- Broadened phase handlers to `BaseException`; a `KeyboardInterrupt` publishes
  an incident while the durable claim remains.
- Added cross-root direct/symlink mutations, a symlinked-`runs` escape test,
  invalid/changed/noncanonical registration incidents, exact surface pins, CLI
  raw-path enforcement, fixed-claim refusals, and interrupt/claim lifecycle
  tests.
- Required the package-derived root to equal Git's checkout top level, closing
  the nested-source-copy alternate-lock escape found in final review.
- Recounted 3,590 tests: 829 unit, 1,278 artifact, 804 integration-PSID,
  520 reproduction-legacy, and 159 oracle-policyengine.
- Passed the complete entry-8 focused scope (163), unit tier (824 plus 5
  skips), artifact tier (1,238 plus 40 skips), repository-wide Black (486
  files), Ruff, and `git diff --check`.
- Wrote the final handoff report to `FINAL_REPORT.md`.

## Next

- Push `sol/entry8-impl` from a network-enabled environment.
- Request PR #286 round-2 re-review.
