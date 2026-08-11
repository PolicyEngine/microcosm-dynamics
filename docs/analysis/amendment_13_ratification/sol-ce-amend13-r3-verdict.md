# RATIFY

I attest branch `claude/ce-design-amendment13` at clean HEAD `d2a7e9c295db0e438457e44351e3493adf2a9751`.

The mode-`100644` governing document is exactly:

- **3,810,536 bytes**
- Git blob `323ce94dafa70b4496f9e1eaa490f16e9707624b`
- SHA-256 `ae939693b8bcd99244135a170fdf268f0120d22a4d5cd857f5fcec525b5c859b`

Its first 3,713,728 bytes are byte-identical to revision 14 and hash to `283a010c1bb135917fd8c1f1aebd1526165f829509d32e7689537167aa8818f5`.

## Enforcement findings

- **§27.7 closure is complete.** The exact grammar captures only eight pin values; normalization preserves every other byte ([validator](/Users/maxghenis/PolicyEngine/social-security-model-worktrees/e13-amend13/scripts/validate_amendment13_execution_law.py:1933), [normalizer](/Users/maxghenis/PolicyEngine/social-security-model-worktrees/e13-amend13/scripts/validate_amendment13_execution_law.py:1993)). Of the 1,131-byte enacted interval, 267 captured bytes are normalized and 864 are hashed. Both round-2 attacks rejected at semantic-projection drift. Exhaustive insertion at every decoded-text gap produced zero surviving projections. No residual unconsumed-text or normative-prose path remains. The committed mutation inserts the `FORGED_RATIFIED_AUTHORITY` attack inside this interval and fails if it survives ([mutation](/Users/maxghenis/PolicyEngine/social-security-model-worktrees/e13-amend13/scripts/validate_amendment13_execution_law.py:7044)).

- **Enrollment is immutably fail-closed.** The law correctly records that no pre-draft cryptographic reviewer root exists ([document](/Users/maxghenis/PolicyEngine/social-security-model-worktrees/e13-amend13/docs/design/covered_earnings_correction.md:51575)). Production authenticates the document-selected implementation and parses its three literal `None` assignments without executing or trusting live module state ([validator](/Users/maxghenis/PolicyEngine/social-security-model-worktrees/e13-amend13/scripts/validate_amendment13_execution_law.py:2946)). Live current and legacy trust-attribute injection still yielded `(None, None, None)`. Even forcing nonempty literal selection reached the unconditional separately-ratified-successor rejection ([loader](/Users/maxghenis/PolicyEngine/social-security-model-worktrees/e13-amend13/scripts/validate_amendment13_execution_law.py:3012)). Neither public validator nor public builder accepts caller trust material; private synthetic helpers emit no authority. The one-actor/two-key mutation genuinely constructs and privately validates the ceremony before requiring public rejection ([mutation](/Users/maxghenis/PolicyEngine/social-security-model-worktrees/e13-amend13/scripts/validate_amendment13_execution_law.py:7144)). Draft status remains `PROSPECTIVE_NONAUTHORITY_UNRATIFIED_DRAFT`, with both emission flags false.

- **Inventory consistency is enforced.** The four authentication schemas and two authentication statuses are expressly qualified as separate exact inventories ([document](/Users/maxghenis/PolicyEngine/social-security-model-worktrees/e13-amend13/docs/design/covered_earnings_correction.md:51769)). The projection enforces uniqueness, disjointness, trusted-literal membership, and exact enactment coverage ([validator](/Users/maxghenis/PolicyEngine/social-security-model-worktrees/e13-amend13/scripts/validate_amendment13_execution_law.py:2068)). Changing the enacted governing schema from `.v1` to an unlisted `.v2` rejected at `enacted identifier inventory consistency drift`.

- **No authentication read remains replace-ref-sensitive.** Production Git is centralized through `git --no-replace-objects` with all ambient `GIT_*` values removed and only `GIT_NO_REPLACE_OBJECTS=1` restored ([wrapper](/Users/maxghenis/PolicyEngine/social-security-model-worktrees/e13-amend13/scripts/validate_amendment13_execution_law.py:2786)). The revision-14 prefix test now uses that wrapper ([test](/Users/maxghenis/PolicyEngine/social-security-model-worktrees/e13-amend13/tests/test_validate_amendment13_execution_law.py:684)). Remaining plain Git calls are nonauthentication observations, negative-input construction, or deliberate scratch-attack controls.

## Identities and invariance

- Constructed law: **1,781,842 canonical bytes**, SHA-256 `95cde20c13ca0c4652b5f108044a2335e2b4093a182de84d9b13e4d12691f100`.
- §§27.3–27.6 and 27.8 are byte-identical to both `fdd5242` and `eae03d9`; only §§27.2 and 27.7 changed.
- Raw-object reconstruction confirmed 28 proof successors, eight terminal fragments, two exact compositions, eight doc-036 corrections, 46 supersessions, 14 overlays, six era seals, and the unchanged five-row continuation projection. Rows 1/14/28, both composition coordinates/hashes, continuation disjointness, and DC-72–77 were spot-recomputed.
- Implementation pin P is `76e7f48ae21232c233029c3b54f0b2f870067169`. Its validator and test blobs, sizes, SHA-256 values, and bytes exactly match the running files. `d2a7e9c` is its document-only child.
- Fix-2 changes only the document, A13 validator/test, and tier metadata. `git diff --check` is clean.
- Strict JSON, canonical JSON, balanced-fence, and exact-walk selection: **8 passed**.
- Black 26.5.1, `-l 79 --check`: **579 files unchanged**.

## Tests

- A13 collection: **34**. All test bodies and both mutation runners are substantively bound; mutation names are appended only after the intended rejection gate.
- Temp-free A13: **23 passed, 11 deselected**.
- Seven semantic mutations and three in-memory enforcement mutations executed and rejected.
- A12: **72 passed, 79 deselected**, including all **71/71** historical mutations.
- Full collection: **5,411**.
- Tier replay: **1 passed, 5,410 deselected**; counts are exactly `1,530 / 2,354 / 848 / 520 / 159`.

The read-only sandbox provided no writable temporary directory, so the three scratch-only SSH/Git enforcement ceremonies could not be independently rerun here. Their fail-if-survives control flow and authentication gates were audited and are non-tautological; this is an environment limitation, not a branch finding.

**Scope:** the Amendment 13 laws and enforcement only. The bytes and full SHA-256 above are attested. Nothing downstream is certified.