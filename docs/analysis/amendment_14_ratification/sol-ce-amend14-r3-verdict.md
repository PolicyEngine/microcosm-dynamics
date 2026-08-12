# RATIFY

I attest clean branch `claude/ce-design-amendment14` at HEAD `e9bd6bb9baf36cf21e0fe1c9b6385f827a3253a8`, equal to its tracking ref.

Candidate identity:

- Mode: `100644`
- Bytes: `3,836,294`
- SHA-256: `c4f3ae022d2e623f4316600e16ec3bded10f0160d197ce64e37f35015e55c92f`
- Git blob: `4a3280c849070359232ab445635e016e98de3981`

Scope: Amendment 14’s laws and enforcement only. This certifies nothing downstream. No rewrite findings.

## Reroute verification

The round-2 B finding is closed.

The regression at [test_validate_amendment13_execution_law.py:387](/Users/maxghenis/PolicyEngine/social-security-model-worktrees/e14-amend14/tests/test_validate_amendment13_execution_law.py:387):

- Retains the private `_public_registry_ratification_context` rejection.
- Separately passes the real, zero-argument public `validate_ratification_operativity()` function to the original rejection checker at lines 399–403.
- Requires the expected `LawError`; `_expect_law_error` raises if either call survives.
- Supplies no synthetic context or binding to the public leg.

The live attack helper at [validate_amendment13_execution_law.py:5610](/Users/maxghenis/PolicyEngine/social-security-model-worktrees/e14-amend14/scripts/validate_amendment13_execution_law.py:5610) creates a genuine clone, forged raw `HEAD`, and Git replacement ref. Lines 5667–5690 prove ordinary Git sees substituted design bytes while `--no-replace-objects` sees the forged bytes. Scratch `ROOT` and registry attack state remain active through both assertions and are restored only at lines 5703–5706.

The fixture patches only the assertion helper. It does not patch or weaken `design_binding`, Git sanitization, the public context loader, closure validation, or `validate_ratification_operativity()`.

Fix-2 made zero production changes:

- Validator at both revisions: blob `dad5a34919624bfa3e4c11d5e37580cacbc9912e`, 231,877 bytes, SHA-256 `c33a1c584c3256aa138b4356c6c81cb3e33ea81f4cf4f2e986350eb2e75d6b91`.
- Registry at both revisions: blob `83d5f45bf58e07514cfb3d5288e67526f3c03b3b`, 51,554 bytes, SHA-256 `25a62eb8e8130937e8b7801ec50a3ac974595e29ae1263aa3775a0d97b6666ce`.
- `git diff --quiet df4dc03..e9bd6bb` over both production files returned success.

## Design and identity discipline

The fix-2 design diff is exactly the single enacted test-pin row at [covered_earnings_correction.md:53091](/Users/maxghenis/PolicyEngine/social-security-model-worktrees/e14-amend14/docs/design/covered_earnings_correction.md:53091):

- Old: blob `8ede1e5ffa98a263cf1d41dfce1140ec6f7f9f15`, 22,153 bytes, SHA-256 `05361bd15473e76b4521c4c4cdce102bf97bf138da18c6b3755c2607728cb424`.
- New: blob `5da8929ec67a31398c7d01b54fec1861dcedc075`, 22,768 bytes, SHA-256 `b0ef913ed01aa5ad2af5fec9d0096e9900ac3ef0d7f072d81b5e0d0b2889f2e4`.

No other design line changed.

Protected identities:

- Normalized Amendment-14 projection is byte-identical before/after fix-2: 25,624 bytes, SHA-256 `8d17464268b95d500dcc4d7640edee0f26180a70172cdb3a3966a8e6d2408062`.
- Revision-15 prefix: 3,810,536 bytes, SHA-256 `ae939693b8bcd99244135a170fdf268f0120d22a4d5cd857f5fcec525b5c859b`, blob `323ce94dafa70b4496f9e1eaa490f16e9707624b`; byte-identical.
- §§27.3–27.6: 48,483 bytes, SHA-256 `115a9b4ba9026b5314a6a8f86bb0b3feeb24ff40e6298b180a580740b6fc54c8`; byte-identical to both `df4dc03` and revision 15.
- Overall revision-15-to-HEAD design diff remains append-only: `+467/-0`.

The active blob-only implementation pins match the working tree and `HEAD`; `_verify_implementation_pins()` passed:

| File | Bytes | SHA-256 | Blob |
|---|---:|---|---|
| Validator | 231,877 | `c33a1c584c3256aa138b4356c6c81cb3e33ea81f4cf4f2e986350eb2e75d6b91` | `dad5a34919624bfa3e4c11d5e37580cacbc9912e` |
| Focused test | 22,768 | `b0ef913ed01aa5ad2af5fec9d0096e9900ac3ef0d7f072d81b5e0d0b2889f2e4` | `5da8929ec67a31398c7d01b54fec1861dcedc075` |

The parsed identity contains only `mode` and `files`; no implementation commit or reachability condition exists.

## Spot-check results

- Registry authentication uses one sanitized launcher at [covered_earnings_correction_registry.py:617](/Users/maxghenis/PolicyEngine/social-security-model-worktrees/e14-amend14/scripts/covered_earnings_correction_registry.py:617). It strips all ambient `GIT_*`, sets `GIT_NO_REPLACE_OBJECTS=1`, and invokes `git --no-replace-objects`; all three registry reads route through it.
- Validator production Git reads use the equivalent launcher at [validate_amendment13_execution_law.py:2804](/Users/maxghenis/PolicyEngine/social-security-model-worktrees/e14-amend14/scripts/validate_amendment13_execution_law.py:2804). The only other validator subprocess is attack-only `_scratch_git`; direct test subprocesses are observational witnesses.
- `_load_canonical_git_json` is absent repository-wide. No active enrollment, SSH, certifier, recording-manifest, signed-record, or reviewer-key machinery remains; only the two expressly historical removed-mutation names survive.
- Exact closure keysets reproduce as 8 top-level, 3 verdict-row, 3 registry-closure, and 5 registry-design keys. Strict canonical parsing, type checks, exact paths, distinct verdicts, byte attestations, commit/parent/tree identity, and revision-16 cross-binding remain enforced.
- The current public call fails closed with `LawError: registry ratification closure binding is missing`.
- Both A13 verdict artifacts are byte-identical to their external source records:
  - 6,207 bytes, SHA-256 `7e0f1ad7faec611a08ed8f0123cc484fe981a0f9681e7cd144f4deafb128dc72`.
  - 5,379 bytes, SHA-256 `6cd4b1e5689985685bf88100b78b20b676ae222a323cec20a6c9097799a75383`.
- The honest property statement remains intact at [covered_earnings_correction.md:52896](/Users/maxghenis/PolicyEngine/social-security-model-worktrees/e14-amend14/docs/design/covered_earnings_correction.md:52896), expressly disclaiming independent-human control and public-key-authenticated reviewer identity.
- Rebuilt canonical fixture: 1,781,842 bytes, SHA-256 `95cde20c13ca0c4652b5f108044a2335e2b4093a182de84d9b13e4d12691f100`, with draft status and both authority/certification false.

## Validation

- Focused module: exactly 52 tests collected.
- Executable focused subset: 39/39 passed.
- Mutations executed directly: 7/7 semantic and 9/9 non-write enforcement attacks rejected at their intended gates.
- Write-dependent attacks: replacement-ref and committed-implementation-blob mutations were source-audited end-to-end. This sandbox has no writable temporary directory, so their execution stopped at `TemporaryDirectory` before attack setup or any assertion. The full focused attempt therefore reported `39 passed, 1 filesystem failure, 12 dependent setup errors`; I do not count those blocked cases as runtime passes.
- A12: 72 passed, 79 deselected—its inventory assertion plus all 71/71 mutations.
- Registry battery: 220/220 passed.
- Full collection/tier policy: 1 passed, 5,428 deselected = 5,429 collected; census `1,530 + 2,372 + 848 + 520 + 159`.
- Strict JSON/canonical/fence checks: 7/7 passed.
- Exact nonvacuous sweep/walk checks: 4/4 passed.
- Black 26.5.1: all 579 files unchanged.
- Ruff 0.16.1: all checks passed.
- Literal `uvx` could not initialize its cache under read-only permissions; the same cached engines were run directly with caching disabled.
- `git diff --check` is clean for worktree, index, fix-2, and the full amendment range.
- Largest tracked file: 45,941,875 bytes; zero files are at or above 50,000,000 bytes.
- Final worktree remains clean at the attested HEAD.