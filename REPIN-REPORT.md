# Revision-20 repin report: Amendment 18

## Status

**LAWFUL-STOP**

The revision-20 ratification-closure and registry-repin ceremony stopped
before its first governed commit. Two independent enacted gates reject the
supplied final ratification inputs. No verdict, receipt, closure, registry,
registry test, design, gate, run, or committed-artifact file was changed.

## Plan and disposition

1. Read §32.5.3, then §§30.2, 30.4, and 31.3, and compare the
   revision-19 precedent at `83df0ef`.
2. Derive the Amendment-18 ratification commit, its sole parent, and the
   design byte identity from raw Git objects.
3. Validate the two supplied final verdicts and the external executed-
   transition receipt before admitting either to the ceremony.
4. Only if those gates passed, commit verdicts, create and commit the
   closure, repin the registry and its exact test mirror, and run the full
   revision-20 validation battery.

Steps 1–3 completed. Step 3 failed closed, so §32.5.3 forbids steps 4 and
later. Creating a closure or repinning around either rejection would be a
workaround rather than execution of the enacted law.

## Raw Git identity derived at execution time

The fetched branch base and `origin/master` both resolved to the #394 squash.
Raw `rev-list`, `ls-tree`, `cat-file`, SHA-256, and byte-count operations
produced:

| Field | Derived value |
|---|---|
| Ratification/operator merge commit | `99fe51c002fb060878812e85da21f9d74813460e` |
| Sole parent | `e9473e07945228cf1c56065f66de7db97ecd7b0c` |
| Design path/mode | `docs/design/covered_earnings_correction.md`, `100644` |
| Design Git blob | `016c0fff757b54da730ae0044216416cde2d2c33` |
| Design byte count | `3,964,278` |
| Design raw SHA-256 | `631d3b2b8ecab1c29ec0595550a6d2b798f49ff96e74c722801d24c48ab111ec` |

The commit has exactly the one parent shown above.

## Supplied input identities

| External input | Bytes | Raw SHA-256 | Disposition |
|---|---:|---|---|
| `sol-ce-amend18-r2-verdict.md` | 4,944 | `a900bbd2fb553af889d77a2b781958cad4afd5556f318bbe30804c208faa3881` | Rejected: missing the final design raw SHA-256 |
| `sol-ce-amend18-r2b-verdict.md` | 5,419 | `3f787b520e50753f63531ef483e608dca80a6df845a981297e3c033e91655611` | Passes the common design-attestation substring check |
| `sol-ce-amend18-executed-transition-receipt-v1.json` | 4,240 | `b527cc1e3a16e47d7b8cc0fad8fbddb42904eb454e69753d30d7e00436eab240` | Rejected: stale pre-fix state and pinned-test identity |

Round-1 verdicts were not admitted. Sections 30 and 32 do not require the
full round history, and the Amendment-17 precedent committed only the final
round used by its closure.

## Lawful-stop finding 1: one verdict does not attest the design SHA

Section 28.2.1 requires each verdict to contain the same exact candidate
design byte count, raw SHA-256, and Git blob OID. Section 30.2.3 carries that
requirement into every non-Amendment-13 closure. The enacted
`_verdict_attests_design` checker enforces the exact first line and all three
values.

The `r2` verdict starts with `# RATIFY` and contains the final formatted byte
count and blob OID, but it never contains the final raw design SHA-256
`631d3b2b...ab111ec`. The parallel `r2b` verdict contains all three values.
Executing the enacted checker produced:

```text
sol-ce-amend18-r2-verdict.md: REJECTED: LawError: verdict artifact does not affirm the closure design attestation
sol-ce-amend18-r2b-verdict.md: ACCEPTED
```

For a second, full closure-validator diagnostic, the canonical closure
constructed from raw #394 ancestry and the two verdicts in the supplied
`r2`/`r2b` order was created in memory only. Its diagnostic identity was 842
bytes, raw SHA-256
`eb4eb8b553a8236b2652838e6493b57f511ef967d1f1a30cdf02d06b120d6993`,
and Git blob `61422f1eee7d047cc3051da70ee66850b41c8747`. Passing those exact bytes to
`_validate_ratification_closure` produced:

```text
closure: REJECTED: LawError: verdict artifact does not affirm the closure design attestation
```

That diagnostic object was not written or committed and is not a closure of
record.

## Lawful-stop finding 2: the executed-transition receipt is stale

Sections 31.3 and 32.5.3 keep the receipt outside candidate bytes, so the
receipt must not be committed. They nevertheless require referees to verify
an exact same-state demonstration made strictly after the final code, test,
formatter, and pin identities. Section 32.5.3 expressly makes a stale test
identity or two state identities unratifiable.

The supplied v1 receipt binds the pre-fix state. Because §31.3 requires the
receipt before the verdicts and operator merge, the relevant comparison is
the final candidate/code-test commit `93392ca...`, not the later #394 squash.
The final candidate and #394 carry the same exact design blob.

| Identity | Receipt v1 | Final candidate identity (`93392ca...`) |
|---|---|---|
| Simulated registry ratification commit | `a195459943cd0b7cb9a362d6a4ae845a76009fef` | `93392ca776e7a53944a5d12150163b998c385bb5` |
| Design raw SHA-256 | `aac8975799083de21ea55960fe116cf4cb8fe078557b53110cb95b3258d14129` | `631d3b2b8ecab1c29ec0595550a6d2b798f49ff96e74c722801d24c48ab111ec` |
| Pinned-test Git blob | `1e8a6edad9757052a6d35ab238b470e7ec8b7b9d` | `38535ad322e836099f8d4200ab5a3fae0a2527b9` |
| Pinned-test bytes | `86,418` | `86,255` |
| Pinned-test raw SHA-256 | `9353ad55e0fa463a44454578a3b1cccb2f2ec1d02505aad40b5210b7d7afbf9e` | `ad38ab4aee3958f60f065024939887b9bab9c608efee663511f2022426ba3729` |

The enacted `_assert_executed_transition_evidence` helper rejected v1 at its
final active-test-pin equality assertion. The fix instruction retained with
the external evidence expressly called for a new uncommitted v2 receipt to
be generated strictly last; that v2 file is absent. Neither supplied final
verdict identifies a post-fix receipt.

## Precedent and per-commit results

The revision-19 lane was a strict three-commit chain:

1. `Add Amendment 17 ratification verdicts`
2. `Add Amendment 17 ratification closure`
3. `Repin covered earnings design to revision 19`

It committed only final-round verdicts, did not commit the external receipt,
and changed only the registry and
`tests/estimates/test_covered_earnings_correction_registry.py` during its
repin commit.

For this attempted revision-20 ceremony:

| Ordered ceremony commit | Result |
|---|---|
| Amendment 18 final verdicts | Not created: the ordered pair fails §28.2.1/§30.2.3 |
| Executed-transition receipt | Correctly not created in-tree: §§31.3.3 and 32.5.3 keep it external; supplied v1 is stale |
| Amendment 18 closure | Not created: enacted closure validation rejects the supplied verdict pair |
| Revision-20 registry repin | Not created: no admissible Amendment-18 closure exists |

## Oracle and validation outputs

The unmodified public oracle over the unchanged production registry remains
lawful and returned:

```text
current_public_oracle_domain= (13, 14, 15, 16, 17)
current_public_oracle_count= 5
```

It cannot lawfully return revision 20 until a valid sixth closure exists.
Collection-only checks of the unchanged checkout recorded:

```text
tests/test_validate_amendment13_execution_law.py: 107 tests collected
tests/estimates/test_covered_earnings_correction_registry.py: 221 tests collected
complete pytest suite: 5,664 tests collected
```

Repository-wide nonmutating hygiene checks completed successfully:

```text
uv run --no-sync black --check . -l 79: clean
uv run --no-sync ruff check .: clean
git diff --check: clean
```

The pinned battery and complete suite were not executed after the dispositive
ratification-input rejection. Their results could validate only the unchanged
revision-19 state and cannot cure either failed Amendment-18 prerequisite.
The revision-20 same-state oracle and zero-nonpass battery are therefore
**not runnable as a lawful ceremony** with the supplied inputs.

## Delivery disposition

No branch push or draft pull request was performed. The requested activation
PR presupposes a complete revision-20 ceremony, while this attempt stopped
before its first governed commit with status `LAWFUL-STOP`.

## Required resumption condition

Do not alter the immutable design to bypass these failures. A receipt
generated now cannot retroactively cure the existing `r2` verdicts or #394.
Resumption requires a new lawful external ratification round in the enacted
order: first a final-state §31.3 receipt kept outside the candidate bytes,
then two fresh closure-admissible verdicts that each attest the exact common
final byte count, raw SHA-256, and blob OID, and then a later single-parent
operator merge carrying that same design blob. A new repin attempt may begin
only after those prerequisites satisfy the enacted chronology, ancestry, and
identity law.
