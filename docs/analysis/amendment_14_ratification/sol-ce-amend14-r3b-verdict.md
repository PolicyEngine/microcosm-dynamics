# RATIFY

No blocking findings. I attest the Amendment 14 document at clean HEAD `e9bd6bb9baf36cf21e0fe1c9b6385f827a3253a8`:

- Size: `3,836,294` bytes
- SHA-256: `c4f3ae022d2e623f4316600e16ec3bded10f0160d197ce64e37f35015e55c92f`
- Git blob: `4a3280c849070359232ab445635e016e98de3981`

## Reroute verification

The replacement-ref regression at [test_validate_amendment13_execution_law.py:387](/Users/maxghenis/PolicyEngine/social-security-model-worktrees/e14-amend14/tests/test_validate_amendment13_execution_law.py:387) now reaches the public `validate_ratification_operativity()` API during the live scratch-repository and replace-ref attack.

It:

- Retains the private-helper assertion as additional coverage.
- Invokes the public API before attack cleanup.
- Traverses the real public registry context and real `registry.design_binding()`—no synthetic binding shortcut.
- Requires the exact missing-binding rejection, so rejection at an unrelated later gate would fail the test.
- Monkeypatches only the test expectation wrapper; no production authentication or validation check is weakened.

The production validator and registry are byte-identical to `df4dc03`:

- Validator blob: `dad5a34919624bfa3e4c11d5e37580cacbc9912e`
- Registry blob: `83d5f45bf58e07514cfb3d5288e67526f3c03b3b`

All authentication-sensitive Git reads use sanitized wrappers, stripping ambient `GIT_*`, setting `GIT_NO_REPLACE_OBJECTS=1`, and passing `--no-replace-objects`. The only other subprocess site is the intentionally adversarial scratch-Git helper. No replace refs were present, and the former `_load_canonical_git_json` orphan is absent.

## Design and identity discipline

The fix-2 design diff is exactly one enacted test-pin row at [covered_earnings_correction.md:53091](/Users/maxghenis/PolicyEngine/social-security-model-worktrees/e14-amend14/docs/design/covered_earnings_correction.md:53091):

- Old: `22,153` bytes, SHA-256 `05361bd15473e76b4521c4c4cdce102bf97bf138da18c6b3755c2607728cb424`, blob `8ede1e5ffa98a263cf1d41dfce1140ec6f7f9f15`
- New: `22,768` bytes, SHA-256 `b0ef913ed01aa5ad2af5fec9d0096e9900ac3ef0d7f072d81b5e0d0b2889f2e4`, blob `5da8929ec67a31398c7d01b54fec1861dcedc075`

The normalized Amendment 14 semantic representation remains `25,624` bytes with SHA-256 `8d17464268b95d500dcc4d7640edee0f26180a70172cdb3a3966a8e6d2408062`.

The current document begins with the exact revision-15 bytes:

- Prefix size: `3,810,536`
- SHA-256: `ae939693b8bcd99244135a170fdf268f0120d22a4d5cd857f5fcec525b5c859b`
- Blob: `323ce94dafa70b4496f9e1eaa490f16e9707624b`

Thus the enacted revision remains an exact prefix and Amendment 14 remains append-only relative to revision 15. Fix-2 changes only the still-prospective Amendment 14 suffix.

Sections 27.3–27.6 are byte-identical across revision 15, `df4dc03`, and HEAD:

- Size: `48,483` bytes
- SHA-256: `115a9b4ba9026b5314a6a8f86bb0b3feeb24ff40e6298b180a580740b6fc54c8`

The blob-only implementation pins match both the working tree and HEAD:

- Validator: `231,877` bytes; SHA-256 `c33a1c584c3256aa138b4356c6c81cb3e33ea81f4cf4f2e986350eb2e75d6b91`; blob `dad5a34919624bfa3e4c11d5e37580cacbc9912e`
- Test: `22,768` bytes; SHA-256 `b0ef913ed01aa5ad2af5fec9d0096e9900ac3ef0d7f072d81b5e0d0b2889f2e4`; blob `5da8929ec67a31398c7d01b54fec1861dcedc075`

## Enforcement spot-checks

- Canonical fixture rebuilt to `1,781,842` bytes, SHA-256 `95cde20c13ca0c4652b5f108044a2335e2b4093a182de84d9b13e4d12691f100`.
- The exact eight-key closure, three-key verdict row, and three-key registry binding schemas match the design and are strictly canonicalized.
- Public operativity validates both ordered A13/A14 closures and currently fails closed with `registry ratification closure binding is missing`.
- A13 verdict pins recomputed byte-exact:
  - `6,207` bytes, SHA-256 `7e0f1ad7faec611a08ed8f0123cc484fe981a0f9681e7cd144f4deafb128dc72`
  - `5,379` bytes, SHA-256 `6cd4b1e5689985685bf88100b78b20b676ae222a323cec20a6c9097799a75383`
- The honest-property statement remains intact: it does not claim independent human review or public-key reviewer authentication.

## Validation

- Focused suite: exactly `52` nodes collected and bound.
- Read-only-safe focused execution: `39` passed.
- Mutations: `16/18` genuinely executed and rejected. The two writable-scratch attacks—replacement-ref and implementation-blob mutation—were source-audited end-to-end because the sandbox could not create temporary directories. Both require the intended rejection gate.
- A12 mutations: `71/71`.
- Registry: `220/220`.
- Full collection: `5,429`.
- Enforced tier census passed: `1,530 / 2,372 / 848 / 520 / 159`, totaling `5,429`.
- Black and Ruff: clean.
- Markdown fences balanced; all `233` tracked JSON files parsed; strict closure JSON checks passed; tracked-file walks were coherent.
- `git diff --check`: clean.
- No tracked file exceeds 50 MiB; largest is `45,941,875` bytes.

One nonblocking documentation observation: [tests/README-tiers.md:42](/Users/maxghenis/PolicyEngine/social-security-model-worktrees/e14-amend14/tests/README-tiers.md:42) still records the older `2,354` artifact and `5,411` total counts. The executable manifest and tier-policy test use and enforce `2,372` and `5,429`. This stale descriptive table is outside the Amendment 14 law/enforcement attestation.

This verdict attests only the exact Amendment 14 laws and their enforcement at the identified HEAD. It certifies nothing downstream and does not declare Amendment 14 operative or confer authority.