# PR #286 referee round-1 implementation report

## Status

All adjudicated implementation fixes are complete and verified locally. No
projection was run. The only execution blocker is the requested push:
`git push origin sol/entry8-impl` fails because this sandbox cannot resolve
`github.com`.

## Fixes

1. **Finding 1 — official determination-year COLAs.**
   `data/external/ssa_cola_history.json:5` now stores the official 1975-2022
   determination-year series, ending at `2022=8.7`; loader semantics are
   direct at `src/populace_dynamics/estimates/parameters.py:144` and hashes
   are pinned at `parameters.py:46-50`. The independent 12-year literal vector
   is at `tests/test_extract_ssa_cola_history.py:132`. Its official
   determination-year entries are `2008=5.8`, `2009=0.0`, and `2010=0.0`;
   the prompt's `2009=5.8` is the corresponding payment-year description,
   not the official determination-year key. Raw SHA-256:
   `12da7f0e0d33fc53eaa31567d86c3cc035a49feefc2e4695bceea3379c2a38db`;
   content SHA-256:
   `8f1d75cab8bd1dba226c83bdff28a0ca1b21167e803eb65ff1d13d5cbe2255e0`.

2. **Finding 2 — SSA COLA/factor rounding order.**
   `src/populace_dynamics/estimates/ledgers.py:502` maintains a stepwise
   dime-floored increased PIA and independently dime-floors the claim-age
   factor result. The worked example is pinned at
   `tests/estimates/test_ledgers.py:151` as `71.4`.

3. **Finding 3 — nonpersistent production coordinator.**
   `src/populace_dynamics/estimates/coordinator.py:456` connects preparation,
   compute, invariant assembly, publication, and incident paths; the public
   sealed entry point is at `coordinator.py:590`, with the CLI at
   `scripts/run_first_estimates.py:1`. The complete ceremony is serialized by
   a transient kernel lock with no state file (`coordinator.py:257`), the full
   registered input-source chain is HEAD-bound (`coordinator.py:51,165`), and
   frozen environment/contract identity is revalidated before publication
   (`coordinator.py:272`). Retry history and prior incident references are
   carried through `src/populace_dynamics/estimates/first_report.py:580` and
   validated at `src/populace_dynamics/estimates/publication.py:1576`.

4. **Finding 5 — production-only opaque parameter loading.**
   Production calls the zero-argument loader only through
   `coordinator.py:139`; injected operations remain behind the test-private
   coordinator. `parameters.py:502` remains the sole bundle constructor.
   Unavailable external installations are narrowly typed at
   `parameters.py:172` so the one permitted retry is reachable without making
   hash/schema failures retryable.

5. **Finding 6 — exact configuration, sidecar, token, and path.**
   Exact canonical registered bytes are validated at
   `src/populace_dynamics/estimates/runner.py:171`; opaque registration and
   precompute tokens are created at
   `src/populace_dynamics/estimates/publication.py:492,526,578`. Full
   environment/contract sidecar validation is at `publication.py:624`,
   production artifact publication requires the token at
   `publication.py:1711`, and the only output is the canonical
   `runs/first_estimates_v1.json` declared at `publication.py:28`.

6. **Finding 8 — adversarial mutation coverage.**
   Stage-D 2-before-3 precedence, empty PMF fail-closed, exact RNG namespace,
   future-earnings exclusion, literal birth-plus-62 PIA year, pre-claim
   payment exclusion, and positive post-claim counts are pinned in
   `tests/estimates/test_career.py:482-524` and
   `tests/estimates/test_ledgers.py:176-287`. Independent spec hashes are at
   `tests/test_first_estimates_runner.py:16-20,183`; the full section-11
   incident mutation battery begins at
   `tests/estimates/test_incident_mutations.py:90`, including exact keys and
   types, canonical names/paths, configuration drift, the outside-echo
   numeric-array guard, retry truth table, partial-path rule, and contiguous
   append behavior.

7. **Finding 7 implementation-only preparation.**
   The three current semantic paraphrases are corrected at
   `src/populace_dynamics/estimates/publication.py:133,175,239`. The complete
   current section-10 table is copied byte-exactly to
   `tests/fixtures/first_estimates_gap_block_v1.md` and independently pinned
   at `tests/estimates/test_gap_block_fixture.py:15-37` with SHA-256
   `e499a338a6de3b92e8e795cb89dadabbeb23036064b5c642461d5a42a032ace0`.
   The coordinator-owned design amendment remains intentionally untouched.

## Verification

- Focused fix-round suite: **146 passed** in 1.05s.
- Unit tier: **824 passed, 5 skipped** in 82.67s.
- Artifact tier: **1,221 passed, 40 skipped** in 52.00s.
- Collection: **3,573 tests** — unit 829, artifact 1,261,
  integration-PSID 804, reproduction-legacy 520, oracle-policyengine 159
  (`tests/tier_counts.json:4`).
- Black `-l 79`: **486 files clean**.
- Ruff: **all checks passed**.
- `git diff --check`: clean.
- Scope: no `engine/`, `harness/`, `gates.yaml`, or `runs/` edits; no
  projection run; no persistent coordinator state.

## Blockers

- **Push only:** DNS/network isolation prevents resolving `github.com`.
- Findings 4 and the design-side portion of finding 7 remain in the
  coordinator's separate design-amendment lane, as adjudicated.
