# Amendment 2, round 4 progress

## State

Round-4 remediation is complete on `claude/ce-design-amendment2` from base
commit `8f55b5436b096930fbc4b51daec7e2969927e7bf`. All three critical and both
high findings pass. The substantive design HEAD is
`8e322f4c9f4aa907f0e390528e4ddd805450c7ef`.

The amendment remains append-only relative to the frozen prefix whose SHA-256
is `f882ea1d67a6d4991838d7b3a40120347d4b1cbb882de796f5d42be1acb40cd7`.
Every finding commit passed the self-audit that no new Section 16 identifier,
projection, or rule reference lacks its complete frozen definition, including
its preimage schema, serialization, and result type.

## Done

- Confirmed the requested branch, base commit, and clean worktree.
- Recorded the five remaining findings and the per-finding commit sequence.
- Closed both named graph-root projections with exact runner objects,
  entrypoints, canonical identity preimages, and typed graph roots.
- Replaced A3's nonexistent capture-sidecar member with the exact descriptor
  array and closed its unique-row/hash predicate.
- Froze the Git-parent generation/registration suffix projection, including
  its rows, canonical value, result law, and current `n=1, r=1` derivation.
- Added the immutable v2 authority-verification successor, complete A1/A3
  capture rows, locator/preimage/predicate/result closure, and exact
  authority-role bindings.
- Closed the preliminary-capture-final-adjudication lineage through one
  unique accepted capture triple and one canonical next-vintage artifact.
- Replaced every §16 live entry-11 lifecycle reference with a strict
  Git-cutoff subject projection that selects one open, unsuperseded exact
  covered-earnings claim and aborts on zero or multiple matches.
- Propagated the derived subject through condition 9, label-state events, the
  calibrated transition predecessor, and the five-field ledger entry while
  preserving forecast supersession/back-link and grading history.
- Verified the current real-state projection selects entry 13 uniquely.
- Rebuilt the normative `gate_specs.v4` replacement domain as seven complete
  six-field rows, including a fitting-free G11 statement and explicit
  `gate_fail` disposition.
- Removed any normative dependence on the separate G11 deviations-ledger row.
- Closed G21 structural validity with one singleton rule registry, complete
  raw-byte/range preimage, six literal predicate equations, one typed result,
  and acyclic mutation-ledger foreign keys.
- Made G21 unfavorable evidence total: results cover the registered mutation
  domain even when observations are missing, out-of-domain observations carry
  exact null/fail tags, and every observed row has one frozen total order.
- Froze all five registration-required V-B role arrays and both complete
  ten-row v1/v2 role maps, including their exact canonical domain hashes.
- Added one closed A1/A3 capture-supplement predicate registry, complete
  manifest/legacy/capture preimage, phase equation, and typed result that
  preserves preliminary negatives and permits only matching v2 supplements.
- Closed every noncapture required-authority result with disjoint A2/A4/A5,
  required-V-B, and family predicate classes, complete semantic payloads,
  unfavorable serialization, and one common typed result.
- Froze the independent 14-family source/method prerequisite registry,
  exact fact arrays, 38-member required-authority order, duplicate-preserving
  candidate construction, and source-versus-method conditional equations.
- Closed the SSA family-source projection against the artifact's actual
  observation schema with exact selectors, value-blind identity rows, total
  duplicate-preserving false results, and frozen current-value hashes;
  methodology facts remain exclusively on the methodology branch.
- Replaced the cyclic/unbound cutoff digest with a complete acyclic cutoff
  identity, binding capture design/cutoff digests and registry versions before
  manifest construction.
- Rebuilt the local unpushed round-4 history so the complete capture-role,
  predicate, source-projection, and required-authority closure is in the same
  introducing finding-2 commit; later findings remain separate commits.
- Verified every round-4 design blob begins with its parent's complete bytes,
  every design delta is insertion-only, and every commit preserves the exact
  579,090-byte frozen prefix.
- Strict-parsed all 47 Section 16 JSON fences with duplicate-key rejection and
  recomputed the displayed graph, gate, role, predicate, family, source,
  authority-domain, and ledger hashes.
- Reproduced the real-state ledger witness at
  `f8c4a32c086eb8ebf3b641a5e08301d0dcd7ba22`: entries 11 and 12 remain
  superseded, the exact candidate array is `[13]`, and zero or multiple open
  unsuperseded matches fail.
- Passed `pytest -q tests/test_forecast_ledger.py` with 5 tests. With
  `PYTHONPATH=src`, all 4,073 repository tests collect; an intentionally
  bounded full run reached 165 passed and 5 skipped with no failure before
  manual interruption. Plain `pytest -q` lacks the repository `src` path and
  therefore reports 73 `ModuleNotFoundError: populace_dynamics` collection
  errors.
- Passed independent closure, capture-constructibility, commit-history, and
  holistic five-finding audits; `git diff --check` is clean.

## Next

None. Ready for review and ratification; no push was performed.
