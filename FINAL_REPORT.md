# PR #286 fix-round-2 implementation report

## Status

All adjudicated round-2 changes are implemented and locally verified on
`sol/entry8-impl`. No projection was run. No LaunchAgent, `nohup`,
`caffeinate`, plist, or other launcher/process-persistence mechanism was added;
those remain run-time coordinator procedure under the scoped ruling. The
adjudicated durable attempt claim is the only new persistent state.

Push is the only blocker. Both `git push --dry-run origin sol/entry8-impl` and
the final `git push origin sol/entry8-impl` failed because the sandbox could
not resolve `github.com`.

## Per-item implementation

1. **Merged the design amendment.**

   Merge commit `05eb400` brings `origin/master` at `ee1221d` into the branch.
   Master's amended design text is present at
   `docs/design/first_estimates_report.md:405,496-497`.

2. **Implemented the exact amendment contract.**

   `src/populace_dynamics/estimates/first_report.py:71` emits exactly
   `{"status": "deferred_to_anchor_extraction"}`. Publication freezes the same
   one-key object at
   `src/populace_dynamics/estimates/publication.py:442,1658`.

   The full amended section-10 table is represented by runtime `GAP_BLOCK` at
   `src/populace_dynamics/estimates/publication.py:67`, including the literal
   F4/F8/F9-sub/F10/F11 Markdown and the two amendment rows at
   `publication.py:255,264`. The byte fixture is exactly 33 lines at
   `tests/fixtures/first_estimates_gap_block_v1.md:1`, with full SHA-256
   `b2330953bf4b517b1bc8f113c596fda0a5d6c60ca240a5cfd232a58346227977`
   independently enforced at
   `tests/estimates/test_gap_block_fixture.py:15-49`.

   Registered configuration records ratification `6586b92` and amendment
   `ee1221d` independently at
   `src/populace_dynamics/estimates/runner.py:26-27,140-144,200-205`.

3. **Incident-accounted all registration bootstrap work.**

   The CLI now forwards only the raw configuration `Path` and has no root
   override (`scripts/run_first_estimates.py:14-45`). Coordinator-owned path
   reading is inside the incident boundary at
   `src/populace_dynamics/estimates/coordinator.py:830-862`; minimal bootstrap
   tokens, decoded-echo preservation, exact byte parsing, and structural
   validation are inside the preparation handler at `coordinator.py:653-769`.

   Invalid, malformed, changed-semantic, and noncanonical byte mutations
   publish incidents and corrected changed bytes require fresh registration at
   `tests/estimates/test_coordinator.py:505-626`.

4. **Sealed repository and path identity.**

   The exact nine-module estimator surface is declared and checked against
   committed `HEAD` at
   `src/populace_dynamics/estimates/coordinator.py:59-69,200-222`.
   Production derives its root from the imported estimates package, requires
   the canonical `src` layout, and requires that root to equal
   `git rev-parse --show-toplevel` at `coordinator.py:332-355`.

   The lock uses the canonical non-symlink `runs/` directory with
   `O_NOFOLLOW`; configuration paths must resolve within the same root
   (`coordinator.py:297-375`). Direct external paths, in-root symlink escapes,
   symlinked `runs/`, and nested source copies are refused at
   `tests/estimates/test_coordinator.py:629-695,792-857`. The CLI's removed
   root override and raw-path handoff are pinned at
   `test_coordinator.py:943-1005`.

5. **Added the durable attempt claim and interrupt accounting.**

   `runs/first_estimates_attempt.claim` is fixed at
   `src/populace_dynamics/estimates/coordinator.py:76` and atomically created
   with `O_EXCL`, file and directory `fsync`, and no automatic removal at
   `coordinator.py:407-465`. The public entry point creates it under the sealed
   lock before configuration reading or operations at `coordinator.py:867-883`.
   Existing same- or different-registration claims fail closed with
   `fresh-registration adjudication` in the error.

   Preparation, compute, invariant, and publication handlers catch
   `BaseException` at `coordinator.py:763-851`. Claim persistence on success,
   `KeyboardInterrupt` incident publication, and claim-blocked retry are
   covered at `tests/estimates/test_coordinator.py:1008-1107`.

6. **Completed the round-2 mutation battery.**

   The coordinator mutation suite covers invalid registration, malformed JSON,
   changed semantics, a byte-only canonicality change, direct and symlinked
   cross-root inputs, symlinked output roots, exact estimator-surface
   completeness, nested checkout roots, CLI root removal, durable claims,
   successful claim persistence, and `KeyboardInterrupt` incidents
   (`tests/estimates/test_coordinator.py:505-1107`). The pre-existing exact
   incident-schema mutations remain at
   `tests/estimates/test_incident_mutations.py:1`.

## Verification

- Entry-8 focused scope: **163 passed** in 1.28s.
- Unit tier: **824 passed, 5 skipped** in 81.86s.
- Artifact tier: **1,238 passed, 40 skipped** in 52.55s.
- Collection: **3,590 tests** — unit 829, artifact 1,278,
  integration-PSID 804, reproduction-legacy 520, oracle-policyengine 159
  (`tests/tier_counts.json:4`).
- Black `-l 79`: **486 files clean**.
- Ruff: **all checks passed**.
- `git diff --check`: clean.
- No projection, external-data tier, or launcher procedure was executed.

## Commits

- `05eb400` — merge `origin/master` / design amendment 1.
- `2c46f35` — create the committed round-2 progress ledger.
- `be49703` — conform runtime and fixtures to amendment 1.
- `3a5d7d1` — seal, incident-account, and durably claim the ceremony.
- `82186d4` — recount the initial round-2 test inventory.
- `d4b29cb` — require the sealed root to equal Git's checkout top level.

## Blockers

- **Push only:** sandbox DNS cannot resolve `github.com`. The worktree is
  otherwise clean and ready for round-2 re-review after this report commit.
