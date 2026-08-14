# RATIFY

Attested candidate: **3,934,849 bytes**, SHA-256 **`29055c5606a54587107498e8adcdbc8546f93caceabe89238975288db72e7fe1`**, Git blob **`84b31290ecd2d1001b6ea802b9a97a86260cdfda`**.

No rewrite findings. Scope is limited to the Amendment-17 laws, enforcement, and required ratification evidence; this certifies nothing downstream.

## Round-2 cures

The public entrypoint at [validate_amendment13_execution_law.py:5130](/Users/maxghenis/PolicyEngine/social-security-model-worktrees/e17-amend17/scripts/validate_amendment13_execution_law.py:5130) now executes, in order:

1. Registry snapshot.
2. Active pin-table parsing.
3. `_verify_implementation_pins`.
4. Closure validation and return.

Independent probes produced:

- Current registry:
  - Raiser: `RuntimeError: PIN_VERIFIER_REACHED`, no oracle answer, one verifier call.
  - Counter: answer `(13, 14)`, one verifier call.
- Exact §31.4 revision-18 context:
  - Raiser: same failure, no answer, one verifier call.
  - Counter: answer `(13, 14, 15, 16)`, one verifier call.

The bound regression at [test_validate_amendment13_execution_law.py:111](/Users/maxghenis/PolicyEngine/social-security-model-worktrees/e17-amend17/tests/test_validate_amendment13_execution_law.py:111) passed normally (`2 passed`). Replacing the entrypoint in memory with its pre-fix body caused both collected nodes to fail with `DID NOT RAISE RuntimeError`. The regression therefore detects non-reachability and remains outside the mutation census.

## Receipt v2

[Receipt v2](/Users/maxghenis/PolicyEngine/social-security-model-worktrees/e17-amend17/sol-ce-amend17-executed-transition-receipt-v2.json) passed the enacted assertion at [test_validate_amendment13_execution_law.py:145](/Users/maxghenis/PolicyEngine/social-security-model-worktrees/e17-amend17/tests/test_validate_amendment13_execution_law.py:145).

- Receipt: 3,456 bytes; SHA-256 `636eb300df8e0a91425c5668b17482fac90314fad08c461eca04611e86ed4cbb`.
- Canonical manifest: 2,307 bytes.
- State SHA-256: `2e4d429ecb75a15579dbf3f2a45523823b147a29108d21895cbbbf8afdebab74`.
- Registry: commit `60289833febdf88cb9d8977ac1282a0f4b97b278`, revision 18, design SHA `17a4bc2b48bd48039ce0777dd22f265eff156fe2484efd6c7b106c5c642dd1b6`.
- Oracle: exactly `(13, 14, 15, 16)`, executed, exit zero.
- Battery: exactly `76/76`; failed, skipped, deselected, xfailed, and xpassed all zero.
- Final test identity: mode `100644`, 59,143 bytes, SHA `b217deff3b3ce3768087e4e244580b79881894b0235e1664a72c9b099e40c255`, blob `223e6300eb9b378bef28aa78314dbe78af34bcba`.

Ordered closure identities matched enacted values:

- A13: 842 bytes / `fce13fc1e5e2b4026a34dab735ca36186b147260bd0a137979aa52711affabd7` / `abc1145fec35af1673e7852d77f701828e3de139`
- A14: 842 / `0770fc470187d41bc32198b1acbad61927f07f27f26192cb5093a30e411d57d4` / `a13e1384d1f81d3072f7ac7af1c0fd547b9c5709`
- A15: 842 / `f48ac7a42178f79665900540701e75bf3cb066778c9a0b75eae18b0fa774049a` / `7ec67cbfa239b57e13f6b1d470c6e143a9be6f05`
- A16: 842 / `5a39ba6965504db9b72a6057f1ac32e547487947662b3528a13ba17a5bab260c` / `24422550fb7d1dc9c33074f2c0ac4ce0c28c6fa5`

All 21 extra/omitted/defaulted schema attacks rejected. All nine declared JSON-integer fields rejected boolean, float, and string-digit substitutions: `27/27`, including the three committed boolean attacks.

The ephemeral scratch HEAD `bb6c1cd9…` is unavailable locally and was not rebuilt. Authentication instead used manifest recomputation, final test identity, revision-18 prefix identity, and enacted closure reconstruction.

The receipt is untracked and absent from candidate `HEAD`. The A17 suffix contains zero occurrences of `636eb300`, `2e4d429e`, `264f20ce`, or `426f27c2`, so there is no circular receipt pin. A non-candidate `refs/codex-salvage/...` child commit contains the same receipt, but it is not an ancestor of candidate HEAD and does not place it in candidate bytes.

## Regression and census integrity

- Six semantic forgeries across document, terminal-A17, and synthetic-successor-A18 contexts: **18/18 rejected**. These included the original three attacks plus new public-verifier, separate-validator-reachability, and bound-regression wording attacks.
- Normalized A17 semantic SHA over ten pin captures: `b2acce3c1e42d1e58b216cb8643fdc927c741b439621ed66053a1973ac092774`.
- A12: 71 attacks, digest `89ff204fad60051c82ea2b3a9e1c95243a5576ae720ecaad1a97174fb71871c8`.
- A13 semantic: 7, digest `2cc59a481bb6d3837090181077cdc3fff7f547d393f20102831f168c296c7242`.
- A15: 11, digest `285f4f349d27099b64053f88f5292890392fd547643b083410c30f0c5b93b1c8`.
- A16: 7, digest `1e00099f636c1a727839ebc298b965cd0981e0ad8f23189367ba7dbd0eddb871`.
- A17: exactly the three enacted names, digest `b19ebcbf47278d63e12bd8021334a88910895bdfe48caf2d49c6bbe3014417e6`.

The reachability regression adds no census name. The four receipt-attack families remain grouped under the third A17 name. The writable receipt’s 76/76 battery authenticates the full inherited 100-name census, digest `fe2efd7b96c24b7cbd3c6ce350d44906eb5a88b8b35ee77565c1b133cbf1f3e3`.

## Delta and identities

Fix-2 is one commit, parent `4de9944491e147129e1f64eeaafac343814b9c3f`, touching only the design, validator, and exact test: **+86/−15**.

| Artifact | Bytes | SHA-256 | Git blob |
|---|---:|---|---|
| Design | 3,934,849 | `29055c5606a54587107498e8adcdbc8546f93caceabe89238975288db72e7fe1` | `84b31290ecd2d1001b6ea802b9a97a86260cdfda` |
| Validator | 305,370 | `149e655309419d2b0e990e1915cca1e99541ea859c62c206418362a52188313b` | `b10a4d092c1e4c7088a78f5c3068a3261804f4a3` |
| Exact test | 59,143 | `b217deff3b3ce3768087e4e244580b79881894b0235e1664a72c9b099e40c255` | `223e6300eb9b378bef28aa78314dbe78af34bcba` |
| Publisher | 111,145 | `2ff0ff39d7ca316fb78c1beb8164300991ea194e803795e642b544bd78b5ef1b` | `8e7550ff71cd43f3acd39b7fd1779b6e3a223581` |

Additional preservation results:

- A16 prefix: byte-identical 3,915,641 bytes; SHA `17a4bc2b…`; blob `114089d9…`.
- §§27.3–27.6: 48,483 bytes; SHA `115a9b4ba9026b5314a6a8f86bb0b3feeb24ff40e6298b180a580740b6fc54c8`.
- Canonical fixture: 1,781,842 bytes; SHA `95cde20c13ca0c4652b5f108044a2335e2b4093a182de84d9b13e4d12691f100`; draft, no authority or certification.
- Publisher is byte-identical across fix-2.
- All three active pin rows match both worktree and HEAD.
- Predecessor pins remain in the immutable prefix with the append-only superseded-by disposition at [covered_earnings_correction.md:55024](/Users/maxghenis/PolicyEngine/social-security-model-worktrees/e17-amend17/docs/design/covered_earnings_correction.md:55024).

## Full validation

- Lawful revision 18: `(13, 14, 15, 16)`.
- Lawful revision 19: `(13, 14, 15, 16, 17)`.
- Wrong count, wrong order, revision 17, and incomplete revision 19: rejected.
- Pinned file collection: 76.
- Read-only subset: `63 passed, 13 deselected`; the excluded nodes are exactly one standalone tempfile attack plus twelve nodes sharing the tempfile enforcement fixture.
- Full read-only attempt: 63 passes, one failure, twelve fixture errors—all solely “no usable temporary directory.”
- Repository collection: 5,551, coherently partitioned as unit 1,530; artifact 2,494; integration-PSID 848; reproduction-legacy 520; PolicyEngine-oracle 159.
- Cached Black 26.5.1: all three pinned Python files unchanged.
- Cached Ruff 0.16.2 with `--no-cache`: all checks passed.
- `git diff --check`: clean.
- Tracked-file walk: 1,006 files, none missing or symlinked; largest is 45,941,875 bytes, below 50,000,000.
- All 509 fenced blocks across 90 tracked Markdown files balanced. Candidate/evidence receipt, manifest, closure, and fixture strict-JSON/canonical walks passed.
- Final worktree status remains unchanged: only the expected untracked receipt.