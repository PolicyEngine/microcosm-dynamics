# RATIFY

I attest the cured bytes at HEAD/origin `e610c8e9608ad496bd5fd7ffb04130c464b41199`. No rewrite findings.

Scope is limited to the Amendment 19 laws, their enforcement, and required ratification evidence. This certifies no R04/R05 passage, downstream certificate, or production outcome.

## Passability adjudication

**Reading A is compelled.**

The fail-closed object is the lawful failure member, but reproducing it passes only the two independent reconstruction subresults. It does not satisfy the conjunctive R04 gate. A19 expressly keeps overall R04 nonpassing, requires a passing normal member for R05, and forbids R05/certificate/Q5/authority emission while purposes remain underdetermined ([design §29.4.4](/Users/maxghenis/PolicyEngine/social-security-model-worktrees/e19-amend19/docs/design/covered_earnings_correction.md:55938), [supersession](/Users/maxghenis/PolicyEngine/social-security-model-worktrees/e19-amend19/docs/design/covered_earnings_correction.md:56213), [terminal effect](/Users/maxghenis/PolicyEngine/social-security-model-worktrees/e19-amend19/docs/design/covered_earnings_correction.md:56291)).

This foreclosure is projection-bound and internally consistent. Four direct attempts to permit failure-arm R04 passage, waive R05’s normal-member requirement, emit R05/certification, or emit Q5/authority were rejected. Reading B is therefore not available and the text is not ambiguous.

## Byte attestation

| Artifact | Bytes | SHA-256 | Git blob |
|---|---:|---|---|
| Design | 4,025,587 | `38139b8ddd24ef7be09e8f149960e8e0b6e39699d84f3783827eff6c294a9ae9` | `1eba7ff6366bad1999de36c9f7261ad6939ad86a` |
| A18 prefix | 3,964,278 | `631d3b2b8ecab1c29ec0595550a6d2b798f49ff96e74c722801d24c48ab111ec` | `016c0fff757b54da730ae0044216416cde2d2c33` |
| A19 suffix | 61,309 | `d9970c6e150aacbba88b0e5fc00fc97886ae01a02600d66acf416960a31e65c6` | — |
| Validator | 475,604 | `e37dd55aa329f16154c01fb3bc6ba5a871f164c42bd9b7d1f255335b0f7f3152` | `d55d77f882101d5f8cc0934417dd5b52973a8eb0` |
| Exact test | 140,910 | `82568780e29ac6d9efe4b03de94fc3325388c7a3cae148197e95d3fb94fd7376` | `2fcea537455b8240e4b1bb065da5bc1a8ed583de` |
| Publisher, unchanged | 111,145 | `2ff0ff39d7ca316fb78c1beb8164300991ea194e803795e642b544bd78b5ef1b` | `8e7550ff71cd43f3acd39b7fd1779b6e3a223581` |

Worktree bytes equal HEAD; HEAD equals origin. All relevant modes are `100644`.

The A18 prefix is byte-identical. The design delta against `ae68be8` is exactly 623 additions and zero deletions.

## Gap authenticity and Limb I

Both revision-20 gaps are genuine:

- The independently reconstructed purpose census is 21,971 prompts: 818 complete-official, 14 mixed, 56 legacy-only, 21,083 missing; hence `U = 21,153`. Of 21,139 prompts lacking an official mapping, exact-text analysis found 234 unique transfers, 12 ambiguous transfers, 20,893 unmatched prompts, and eight mapped-text conflict classes. No `semantic_bindings` keys exist. Revision 20 therefore supplied no total lawful classifier ([enacted census](/Users/maxghenis/PolicyEngine/social-security-model-worktrees/e19-amend19/docs/design/covered_earnings_correction.md:55773)).
- Revision 20 required hierarchy rows containing proof ID `A`, digest `D` over those rows, search material containing `D`, and an `A` preimage containing that search material. This is the asserted `D → A → search(D) → A` cycle, with no pre-A19 staging rule.

Independent reconstruction from the authenticated source produced:

- Ten-key failure member: exactly 877 canonical bytes, SHA-256 `1651c50ff1f171ac420e55982cb060db70946f9283999c3d9edb2fa140d467c5`.
- Six-key identity: exactly 351 canonical bytes, SHA-256 `077c6a19e44d8abdf96422a8d2d203fdf263ecbbfb70cb9bb3dc9522a3dcd2bd`.

Two fresh derivations were byte-identical. The source-ordered disposition is selected before `O_H`, `O_P`, semantic bindings, or hierarchy construction ([selection rule](/Users/maxghenis/PolicyEngine/social-security-model-worktrees/e19-amend19/docs/design/covered_earnings_correction.md:55868)). It creates neither a default purpose nor a `no_purpose` fact; A19 expressly distinguishes silence from `no_purpose` ([design](/Users/maxghenis/PolicyEngine/social-security-model-worktrees/e19-amend19/docs/design/covered_earnings_correction.md:55853)).

All 73 pass-only authority-header keys were individually injected and rejected, 73/73. Removing each of the seven A12 row-family nonexecution requirements was also rejected, 7/7.

## Limbs II and III

The staged digest recomputation matches the enacted worked identity:

- `D0 = b3789fc44458bf3f361242ac3b891a357de9640eaf72f9ec4f103b7378f74af6`
- Proof ID: `psid-absence-proof:f374f82fcbbbc2757e85568e380a75061d4707a7467650ceb9f09382638e9101`
- `D1 = 4dd38d95cb08aff565edce70b716bb9f30aef607dcddc2e0c1f51cb8a1bbf453`

The resulting dependency graph is acyclic:

`source/H/O_H/O_P → B → D0 → search → proof IDs → final rows → D1 → downstream digests`

No other member-schema digest remains circular. Fixed-point selection and placeholders are forbidden ([staging law](/Users/maxghenis/PolicyEngine/social-security-model-worktrees/e19-amend19/docs/design/covered_earnings_correction.md:55971)).

Active successor routing uses only `A20_SUCCESSOR_PROGRAM_STOP` ([routing](/Users/maxghenis/PolicyEngine/social-security-model-worktrees/e19-amend19/docs/design/covered_earnings_correction.md:56074)). A18’s `A19_SUCCESSOR_PROGRAM_STOP` survives solely as immutable historical material, historical comparison, and negative mutation input. No live consumer reaches it.

## Projection, census, and receipt

Whole-document, terminal-A19, and synthetic-successor-A20 routes all accepted the authentic bytes. Six independent forgeries—member identity, disposition schema, staging rule, active stop identifier, battery count, and supersession row—were rejected in all three contexts: 18/18.

The normalized A19 semantic identity is 61,111 bytes and SHA-256:

`1af9e180f4467a2c1817a12b515112dfaf96e2bcc72519bc2bde4a0423e5296d`

Its movement from `d4740a02964d7dbd074c62260a0f7753e9e77105375a208446b2ecc889ea25e7` is exactly four opening-fence labels changing from `~~~json` to `~~~text`; normalizing those labels makes the old and new suffixes byte-identical. The established A12–A18 convention contains 100 text fences and zero JSON fences; A19 contains 19 text fences and zero JSON fences. The mandatory strict-fence test passes.

The A19 census is exactly 151 canonical bytes, SHA-256 `002aa021325c18e311cc778562ad0e937468a90c378db0740290fcf617929101`, with exactly:

1. `source_purpose_totality_or_binding_disposition_forged`
2. `hierarchy_preproof_final_digest_order_forged`
3. `r06_successor_program_stop_numbering_forged`

Each name is appended only after its grouped attacks pass. The inherited 100-name census (`fe2efd7b…`) and A16/A17/A18 counts `7/3/3`, including A18 `1bf9f6d3…`, remain unchanged.

A19 is activation-affecting, so §31.3 evidence is required. Receipt v2 validates:

- Receipt: 4,633 canonical bytes, SHA-256 `fd54fca80700441f5e19ab1a9c0cb3155a12f1f783f91201e1af10eab72482f0`.
- Canonical manifest: 3,472 bytes, state SHA-256 `ab58cb3b1f2d79acd9763decbed232a89190f728ae1645622d3c2918611746c1`.
- Simulated closures exactly `(13..19)`.
- Battery exactly `201 passed / 0 nonpassing`.
- Design and test identities equal the final cured pins.
- The preserved scratch tree independently returns `(13..19)`.

The worktree receipt is byte-identical to the external [v2 receipt](/Users/maxghenis/m6-sol-lanes/e8-ops/sol-ce-amend19-executed-transition-receipt-v2.json). V1 is stale and binds the superseded round-1 design/commit/state. No receipt, state, scratch-head, closure, or verdict identity appears in the A19 suffix.

## Delta and validation

The reconciliation commits contain only the lawful revision-20 rebase changes:

- `b7e10ee`: design changes the ratified boundary from revision 19/closures 13–17 to revision 20/closures 13–18; validator enforces the new boundary, arithmetic, and stale attacks; the exact test updates those revision-20 expectations.
- `d40b496`: registry handling changes from obsolete ratified-revision-19/prospective-A18 routing to either exact ratified revision 20 or exactly one prospective A19 suffix, authenticating the revision-20 SHA/blob; its test covers the real prefix and malformed-prefix rejection.

The Black-only change is AST-preserving against the round-1 validator; final AST differences are limited to the normalized semantic SHA and fence-parser literals required by the fence repair.

Validation evidence:

- Production oracle: exactly `(13,14,15,16,17,18)`.
- Registry battery: 221 passed.
- Strict-fence test: passed.
- Focused member/passability tests: 24 passed.
- Focused staging/successor tests: 25 passed.
- Historical reproduction tests: 2 passed.
- Collection: 5,758, exactly `1,563 / 2,668 / 848 / 520 / 159`.
- Final complete-suite record: **5,667 passed, 91 known skips, zero failures**.
- `git diff --check`: clean.
- No file exceeds 50 MB.
- §§27.3–27.6, canonical fixture behavior, and publisher are unchanged.

The read-only environment could not initialize any temporary directory. Consequently, a fresh 201-test module attempt reported `184 passed, 1 failed, 16 errors`; all 17 nonpasses were exclusively OS-level temporary-directory failures in temp-backed replacement/census fixtures, with no ordinary assertion failure. The preserved writable same-state run and validated receipt establish 201/201.

Exact cached `uvx` execution of Black 26.5.1 and Ruff 0.16.3 was likewise blocked from initializing its cache. The recorded cured run is Black 26.5.1 clean and Ruff 0.16.3 clean; locally installed Ruff 0.15.0 also passed with `--no-cache`. Installed Black 25.11.0 reports only the expected version-skew formatting difference in the validator, whose AST equality was independently confirmed.

**Final verdict: RATIFY Amendment 19 at design SHA-256 `38139b8ddd24ef7be09e8f149960e8e0b6e39699d84f3783827eff6c294a9ae9`.**