# RATIFY

I attest branch `claude/ce-design-amendment17` at exact HEAD `81e379f0f04008da072f74d9257c72f4a899b27f`.

## Byte identity

| Artifact | Bytes | SHA-256 | Git blob |
|---|---:|---|---|
| [Design](/Users/maxghenis/PolicyEngine/social-security-model-worktrees/e17-amend17/docs/design/covered_earnings_correction.md:54661) | 3,934,849 | `29055c5606a54587107498e8adcdbc8546f93caceabe89238975288db72e7fe1` | `84b31290ecd2d1001b6ea802b9a97a86260cdfda` |
| [Validator](/Users/maxghenis/PolicyEngine/social-security-model-worktrees/e17-amend17/scripts/validate_amendment13_execution_law.py:5130) | 305,370 | `149e655309419d2b0e990e1915cca1e99541ea859c62c206418362a52188313b` | `b10a4d092c1e4c7088a78f5c3068a3261804f4a3` |
| [Exact test](/Users/maxghenis/PolicyEngine/social-security-model-worktrees/e17-amend17/tests/test_validate_amendment13_execution_law.py:111) | 59,143 | `b217deff3b3ce3768087e4e244580b79881894b0235e1664a72c9b099e40c255` | `223e6300eb9b378bef28aa78314dbe78af34bcba` |
| Publisher | 111,145 | `2ff0ff39d7ca316fb78c1beb8164300991ea194e803795e642b544bd78b5ef1b` | `8e7550ff71cd43f3acd39b7fd1779b6e3a223581` |

All are mode `100644`; every active pin matches both worktree and HEAD bytes.

The first 3,915,641 design bytes are byte-identical to Amendment 16: SHA-256 `17a4bc2b48bd48039ce0777dd22f265eff156fe2484efd6c7b106c5c642dd1b6`, blob `114089d99b83c5073e21b6fb64cd701719ac5741`. Other identities:

- Ten-pin-normalized A17 semantic SHA: `b2acce3c1e42d1e58b216cb8643fdc927c741b439621ed66053a1973ac092774`.
- §§27.3–27.6: 48,483 bytes, SHA-256 `115a9b4ba9026b5314a6a8f86bb0b3feeb24ff40e6298b180a580740b6fc54c8`.
- Canonical fixture: 1,781,842 bytes, SHA-256 `95cde20c13ca0c4652b5f108044a2335e2b4093a182de84d9b13e4d12691f100`.

## Round-2 cures

The public path now obtains one registry snapshot, parses the active pin table, executes `_verify_implementation_pins`, and only then enters closure validation or returns.

| Context | Raiser substitution | Transparent wrapper |
|---|---|---|
| Current registry | `RuntimeError("PIN_VERIFIER_REACHED")`; no answer | `(13, 14)`, calls `1` |
| Exact §31.4 revision 18 | Same exception; no answer | `(13, 14, 15, 16)`, calls `1` |

Replacing the entrypoint in memory with the old verifier-bypassing implementation made both collected reachability tests fail with `DID NOT RAISE RuntimeError`. The regression therefore detects non-reachability rather than merely finding an indirect verifier call.

## Executed-transition receipt

[Receipt v2](/Users/maxghenis/m6-sol-lanes/e8-ops/sol-ce-amend17-executed-transition-receipt-v2.json) passes the enacted `_assert_executed_transition_evidence` against the final test pin.

- Receipt: 3,456 bytes, SHA-256 `636eb300df8e0a91425c5668b17482fac90314fad08c461eca04611e86ed4cbb`.
- Canonical manifest: 2,307 bytes, SHA-256/state identity `2e4d429ecb75a15579dbf3f2a45523823b147a29108d21895cbbbf8afdebab74`.
- Registry: commit `60289833febdf88cb9d8977ac1282a0f4b97b278`, revision `18`, design SHA `17a4bc2b48bd48039ce0777dd22f265eff156fe2484efd6c7b106c5c642dd1b6`.
- Oracle: exactly ordered `(13, 14, 15, 16)`.
- Battery: `76/76`; failed, skipped, deselected, xfailed, and xpassed all zero.

Reconstructed closure identities exactly match enacted values:

| Amendment | Bytes | SHA-256 | Git blob |
|---:|---:|---|---|
| 13 | 842 | `fce13fc1e5e2b4026a34dab735ca36186b147260bd0a137979aa52711affabd7` | `abc1145fec35af1673e7852d77f701828e3de139` |
| 14 | 842 | `0770fc470187d41bc32198b1acbad61927f07f27f26192cb5093a30e411d57d4` | `a13e1384d1f81d3072f7ac7af1c0fd547b9c5709` |
| 15 | 842 | `f48ac7a42178f79665900540701e75bf3cb066778c9a0b75eae18b0fa774049a` | `7ec67cbfa239b57e13f6b1d470c6e143a9be6f05` |
| 16 | 842 | `5a39ba6965504db9b72a6057f1ac32e547487947662b3528a13ba17a5bab260c` | `24422550fb7d1dc9c33074f2c0ac4ce0c28c6fa5` |

All closed keysets matched. Twenty-four extra/omitted/defaulted-key attacks and 31 boolean/float/string type attacks rejected, including the three committed boolean substitutions.

Scratch HEAD `bb6c1cd9137af6ecce1c0aa137424611d3b1dd02` is absent from the available object database and cannot be rebuilt read-only. I therefore authenticated it through canonical-manifest recomputation and registry, design, closure, verdict, and final-test identity cross-checks.

The receipt is absent from the candidate index, HEAD, and branch history; its worktree copy remains `??`. A tool-generated local salvage ref contains a WIP snapshot, but it is unreachable from the candidate branch and is not part of candidate bytes. The A17 suffix contains none of `636eb300`, `2e4d429e`, `264f20ce`, or `426f27c2`.

## Regression and census results

- Six semantic forgeries—including the original three plus direct-execution wording, semantic-verifier reachability, and bound-regression wording—rejected in all three document/A17/A18 contexts: `18/18`.
- A17 inventory remains exactly three names, digest `b19ebcbf47278d63e12bd8021334a88910895bdfe48caf2d49c6bbe3014417e6`.
- Temp-free executions: A12 `71/71`, A13 semantic `7/7`, A15 `11/11`, A16 `7/7`, A17 `3/3`, all with exact digests.
- The A14 tempfile attack prevents the complete inherited child census in this sandbox. The enacted `100/100` identity `fe2efd7b96c24b7cbd3c6ce350d44906eb5a88b8b35ee77565c1b133cbf1f3e3` and unchanged, freshly pin-verified publisher stand in as specified.
- Reachability and schema/type regressions do not inflate any census.

Transition checks accepted revision 18 as `(13,14,15,16)` and lawful revision 19 as `(13,14,15,16,17)`. Wrong-count, wrong-order, revision-17, and incomplete-revision-19 variants all rejected at the intended gates.

## Remaining validation

- Exact battery collection: `76`.
- Read-only subset: `63 passed, 13 deselected`; the 13 excluded cases are exactly the tempfile-dependent cases.
- Repository collection: `5,551`.
- Tier census: unit `1,530`; artifact `2,494`; integration-PSID `848`; reproduction-legacy `520`; PolicyEngine-oracle `159`.
- Cached Black `26.5.1`: clean.
- Cached Ruff `0.16.2`: clean.
- `git diff --check`: clean.
- Fix-2: one commit, exactly three tracked files, `+86/−15`.
- Publisher is byte-identical at revision 18, fix-2 parent, and HEAD.
- Predecessor pins remain append-only historical rows with explicit supersession.
- Markdown fences balance globally; candidate receipt/manifest/closures strict-parse canonically.
- Largest tracked file: 45,941,875 bytes, below 50 MB.

This ratifies only the exact Amendment-17 laws, enforcement, and required ratification evidence at the attested bytes above. It certifies no downstream registry repin, closure of record, production result, or later execution.