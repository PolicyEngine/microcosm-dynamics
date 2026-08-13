# RATIFY

I ratify HEAD `c3f4c4208591e8246302186b90c9d021f80d92ea` on `claude/ce-design-amendment15`.

Candidate identity:

- Bytes: `3,881,111`
- SHA-256: `556311b72ec6c8e30eeda4b0f602e0f7f43b9d080c2454966fa3dda3a561d16e`
- Git blob: `50a2a14e1c8845d342dca83559688866e97dc4a7`

## Structural cure

The implementation satisfies the claimed sequence in [build_amendment13_tier2_repairs.py](/Users/maxghenis/PolicyEngine/social-security-model-worktrees/e15-amend15/scripts/build_amendment13_tier2_repairs.py:1659):

1. It captures the enacted three-row implementation pin at definition time.
2. Before launching the census, it verifies the publisher’s regular-file status, mode-`100644` HEAD entry, working-tree/HEAD byte equality, byte size, SHA-256, and Git blob.
3. Only then does it launch the captured repository Python as `-I -B <verified publisher> --emit-complete-mutation-census`, using an environment stripped of inherited `GIT_*` variables except the newly set `GIT_NO_REPLACE_OBJECTS=1`.
4. It requires exit zero and empty stderr, then strictly authenticates canonical JSON: exact schemas and keysets, types, component order, unique names, counts, component digests, inherited/A15 exact names, and aggregate digest.

The committed structural mutations passed in the read-only harness:

- Rebinding `_execute_complete_mutation_names` and all public component runners did not affect the authenticated result.
- Rebinding public `run_complete_mutation_census` and the public narrow-predicate names did not affect the certificate compositor’s captured graph.
- Tampered publisher bytes were rejected before any child invocation.
- Forged subprocess JSON and the four wrong-digest/missing-key/extra-key/wrong-schema variants were rejected.
- The child command and sanitized environment were independently asserted.

The remaining authenticated parent links are definition-bound:

- A15 fixed runner: binding table, projection validator/path, executor, domain digest; each binding contains its name, preparation, gate, exception class, and message predicate.
- Census protocol: A12 runner; law build/validation; A13, A14, and A15 runners; composition, canonicalization, digest, strict-load hooks, type checks, pin verification, Git wrapper, environment, executable, subprocess operation, and evidence authenticator.
- Certificate compositor: authenticated census plus top-level, ratification, source, member, reconstruction, gate, Git-attestation, lifecycle, census, and integrity predicates and their constants/helpers.

A recursive inspection traversed 43 function objects, including 31 factory-local authenticated functions; every factory-local function in the parent census and certificate graphs had zero module-global references.

## Threat-model boundary

The enacted boundary is explicit and accurate in [§29.4.7](/Users/maxghenis/PolicyEngine/social-security-model-worktrees/e15-amend15/docs/design/covered_earnings_correction.md:53894). It covers supported interfaces, census/runner substitution, call-time module-global rebinding, and publisher-byte tampering through pin verification plus a fresh interpreter. It expressly excludes arbitrary patching of closure cells, function objects, interpreter memory, or the Python runtime. That matches the implementation; there is no overclaim.

## Census and regression evidence

The ordered domains reconcile exactly:

- Amendment 12 historical: `71`, digest `89ff204fad60051c82ea2b3a9e1c95243a5576ae720ecaad1a97174fb71871c8`
- Amendments 13/14 inherited: `18`, digest `03495fb62524cc9b5877fd7baf085b9d69a441a4fcbadc9cf1a29ee35d2f06d3`
- Amendment 15: `11`, digest `285f4f349d27099b64053f88f5292890392fd547643b083410c30f0c5b93b1c8`
- Aggregate: `100` names, `100` unique, digest `fe2efd7b96c24b7cbd3c6ce350d44906eb5a88b8b35ee77565c1b133cbf1f3e3`

The production path contains no cache or constant-return bypass: child emission always calls the four real runners, and the public path always performs pin verification, subprocess execution, and authentication. The only caches found are test-helper caches. The expected census constant is used as an equality target and as the post-authentication projection, not as a pre-execution shortcut.

The full public census was attempted for 322.79 seconds. It failed closed when an Amendment-14 mutation required `tempfile.TemporaryDirectory`; this read-only sandbox exposes no usable temporary directory. No partial census was returned or accepted. Therefore I do not claim an independent reproduction of the reported 317-second standalone completion.

Other verification:

- 504 tests collected.
- 458 read-only-safe tests passed; 46 write/full-census-dependent tests were deselected.
- An additional focused strict-JSON, canonicalization, fence, structural-walk, and blob-limit run passed 9/9.
- Black: 583 files unchanged.
- Ruff: all checks passed.
- `git diff --check`: clean.
- Live Git-order validation: `seals_committed`, specifically through `ordered_ceremony_branch_attestation_v1`.
- 1,006 tracked files; none at or above 50 MB; largest is 45,941,875 bytes.
- Final worktree clean.

## Delta and identities

Only the five claimed design, publisher, validator, and test files changed. The attestation/receipt and merge-mode text, certification schema outside the census cure, integrity tail, §29.5.2, and §§29.6–29.8 are byte-identical to `fd29740`.

Commit `c3f4c42` makes the necessary pin-capture alignment: it states definition-time capture, updates the validator pin after formatting, and updates the Amendment-15 semantic digest. Net of the fix range, the validator changes only the two-to-three-row pin parser/verifier, seven-to-ten normalized pin values, publisher row, and resulting semantic pin; its test switches to the active Amendment-15 three-row domain.

Additional identities:

- Revision-16 prefix: `3,836,294` bytes, SHA-256 `c4f3ae022d2e623f4316600e16ec3bded10f0160d197ce64e37f35015e55c92f`, blob `4a3280c849070359232ab445635e016e98de3981`; byte-identical.
- Append-only delta from revision 16: 787 added lines, zero deletions, one Amendment-15 boundary, terminal LF.
- §§27.3–27.6: 48,483 bytes, SHA-256 `115a9b4ba9026b5314a6a8f86bb0b3feeb24ff40e6298b180a580740b6fc54c8`; byte-identical.
- Amendment-15 normalized projection: `a1e7bcb2aabc2b43cc92b09e1d8bf96d644d377ae70d81d9c5f40d7fafa94f3b`.
- Canonical fixture: 1,781,842 bytes, SHA-256 `95cde20c13ca0c4652b5f108044a2335e2b4093a182de84d9b13e4d12691f100`; prospective, nonauthority, uncertified.
- Exact `OPERATIVE` occurrences: two.

No findings. This ratification covers only the Amendment-15 laws and their enforcement. It certifies nothing downstream.