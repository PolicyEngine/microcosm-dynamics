# RATIFY

I attest the Amendment 15 document at HEAD `c3f4c4208591e8246302186b90c9d021f80d92ea`:

- Bytes: `3,881,111`
- SHA-256: `556311b72ec6c8e30eeda4b0f602e0f7f43b9d080c2454966fa3dda3a561d16e`
- Git blob: `50a2a14e1c8845d342dca83559688866e97dc4a7`
- Mode: `100644`

No findings.

## Structural cure

The cure closes R3-B-1:

- The [publisher-pin verifier](/Users/maxghenis/PolicyEngine/social-security-model-worktrees/e15-amend15/scripts/build_amendment13_tier2_repairs.py:1659) uses the definition-time-captured enacted pin and, before execution, checks the regular-file mode, working-tree size/SHA/blob, exact `HEAD` tree entry, and `git show HEAD:<path>` byte equality.
- The [public census runner](/Users/maxghenis/PolicyEngine/social-security-model-worktrees/e15-amend15/scripts/build_amendment13_tier2_repairs.py:1728) then invokes the verified file in a fresh process as the required repository interpreter with `-I -B`. It removes every inherited `GIT_*` variable and sets `GIT_NO_REPLACE_OBJECTS=1`.
- The [stdout authenticator](/Users/maxghenis/PolicyEngine/social-security-model-worktrees/e15-amend15/scripts/build_amendment13_tier2_repairs.py:1550) rejects duplicate keys, non-finite numbers, trailing/noncanonical bytes, wrong keysets, wrong schema, wrong component ordering or names, count/uniqueness drift, and component or aggregate digest drift.
- No public authenticated route returns a cached or constant census without first executing and authenticating the child. The stored expected census is only the post-execution comparator.
- Rebinding module globals `_execute_complete_mutation_names`, the component runners, or `run_complete_mutation_census` did not reach the authenticated result. The probes recorded zero calls to the rebound functions.
- The committed tampered-publisher and forged-subprocess-JSON mutations reject. The named Amendment 15 global-rebinding mutation passed with actual execution.

The remaining in-process links are definition-time bound:

- Amendment 15 runner: design path, projection validator, mutation executor, fixed projection, mutation-domain digest, and all eleven bindings including their names, callbacks, gates, expected exceptions, and messages.
- Complete-census closure: component runners; execution-name collector; component and aggregate composers; evidence/emitter; canonical JSON, duplicate/nonfinite handlers and authenticator; environment sanitizer; Git wrapper; publisher-pin verifier; subprocess runner; interpreter/root/path/schema constants; expected names, counts, digests, and captured pin table.
- Certificate closure: the original census runner; JSON, mapping and hashing primitives; deep-copied ratification, source, member, reconstruction, gate, attestation and integrity constants; and the locally defined top-level, ratification, source, member, reconstruction, gate, mutation-census and integrity validators.

## Threat-model boundary

The [enacted boundary statement](/Users/maxghenis/PolicyEngine/social-security-model-worktrees/e15-amend15/docs/design/covered_earnings_correction.md:53894) is accurate. It claims protection for supported interfaces, call-time module rebinding, runner substitution, and tampered publisher bytes through the pin and fresh interpreter. It expressly excludes arbitrary mutation of closure cells, function objects, interpreter memory, or runtime internals.

That matches the implementation. Defeating the remaining chain requires precisely the arbitrary same-process/runtime patching the text disclaims; the text does not overclaim resistance to it.

## Census and regression evidence

Reconciled mutation domains:

| Component | Count | SHA-256 |
|---|---:|---|
| Amendment 12 | 71 | `89ff204fad60051c82ea2b3a9e1c95243a5576ae720ecaad1a97174fb71871c8` |
| Amendments 13–14 | 18 | `03495fb62524cc9b5877fd7baf085b9d69a441a4fcbadc9cf1a29ee35d2f06d3` |
| Amendment 15 | 11 | `285f4f349d27099b64053f88f5292890392fd547643b083410c30f0c5b93b1c8` |
| Aggregate | 100 unique | `fe2efd7b96c24b7cbd3c6ce350d44906eb5a88b8b35ee77565c1b133cbf1f3e3` |

The exact suite collects 504 tests. In this read-only environment, 462 sandbox-compatible tests passed; 42 scratch-repository cases could not complete because no writable temporary directory exists. The full fresh-process rebinding test ran for 289.31 seconds before reaching the inherited Amendment 14 `TemporaryDirectory` operation and failing solely with “No usable temporary directory.” This is an audit-environment restriction, not an implementation failure.

Additional checks:

- Live Git-order attestation test passed for the intended reason.
- `OPERATIVE` occurs exactly twice; Amendments 13 and 14 both evaluate operative.
- Strict JSON, fences, canonical fixture, bounded-walk and blob-limit tests passed.
- Black: all 583 files unchanged.
- Ruff: all checks passed.
- `git diff --check`: clean.
- No tracked file reaches 50 MB; largest is `45,941,875` bytes.
- Worktree remained clean.

## Delta and identities

- Fix range changes only the design document, publisher, validator, and their two test files.
- Attestation, receipt, merge-mode, §§29.4.1–29.4.6, and the unaffected §29.4.7 integrity tail are byte-identical to `fd29740`.
- Commit `c3f4c42` changes the law to say the publisher pin is captured at definition time, updates the resulting semantic projection/pin, and contains only semantics-neutral formatter movement otherwise. This is exactly the cross-process design requirement.
- Revision-16 prefix: `3,836,294` bytes, byte-identical; SHA-256 `c4f3ae022d2e623f4316600e16ec3bded10f0160d197ce64e37f35015e55c92f`.
- §§27.3–27.6: byte-identical; SHA-256 `115a9b4ba9026b5314a6a8f86bb0b3feeb24ff40e6298b180a580740b6fc54c8`.
- Amendment 15 normalized projection: `a1e7bcb2aabc2b43cc92b09e1d8bf96d644d377ae70d81d9c5f40d7fafa94f3b`.
- Canonical fixture: `1,781,842` bytes; SHA-256 `95cde20c13ca0c4652b5f108044a2335e2b4093a182de84d9b13e4d12691f100`.
- Relative to revision 16, the document is append-only: 787 insertions, zero deletions.

**Ratification scope:** the Amendment 15 laws and their enforcement only. This verdict certifies nothing downstream.