# Amendment 2, round 4 progress

## State

Round-4 remediation is in progress on `claude/ce-design-amendment2` from
base commit `8f55b5436b096930fbc4b51daec7e2969927e7bf`.

The amendment remains append-only relative to the frozen prefix whose SHA-256
begins `f882ea1d`. Every finding commit must pass a self-audit that no new
Section 16 identifier, projection, or rule reference lacks its complete frozen
definition, including its preimage schema, serialization, and result type.

## Done

- Confirmed the requested branch, base commit, and clean worktree.
- Recorded the five remaining findings and the per-finding commit sequence.
- Closed both named graph-root projections with exact runner objects,
  entrypoints, canonical identity preimages, and typed graph roots.
- Replaced A3's nonexistent capture-sidecar member with the exact descriptor
  array and closed its unique-row/hash predicate.
- Froze the Git-parent generation/registration suffix projection, including
  its rows, canonical value, result law, and current `n=1, r=1` derivation.

## Next

1. Define authority-role resolution and lawful append-only capture
   incorporation.
2. Replace fixed ledger-entry references with the structural publication
   subject.
3. Replace G11 as the seventh complete `gate_specs.v4` row.
4. Close G21 structural validity.
5. Run strict JSON, append-only-prefix, closure, repository-state, and
   whitespace validation; record final dispositions.
